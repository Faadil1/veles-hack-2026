"""Hyperion Steward turn handling.

Routing order for each user message:
  1. A pending confirmation is answered first (deterministic yes/no, EN/FR/ES).
  2. Deterministic commands that must never depend on a model: undo, check/validate <file>.
  3. Otherwise the language model plans with tools. Every tool that changes the workspace goes through SafeOps.
  4. If the model is unavailable, a degraded deterministic mode answers doc questions and explains the outage;
     it never guesses a write.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from . import intents, guardrail, patching, runnability, spec, templates
from .engine import SafeOps, Session
from .ide import IdeClient
from .llm import LLM, LLMError, LLMTurn
from .retrieval import DocsIndex

MAX_STEPS = 8
CONTEXT_TOKENS = int(os.environ.get("STEWARD_CONTEXT_TOKENS", "8192"))  # legion1 llama3.1: 8192-token context
OUTPUT_TOKENS = int(os.environ.get("STEWARD_MAX_OUTPUT_TOKENS", "1536"))
TOOL_RESULT_CHARS = int(os.environ.get("STEWARD_TOOL_RESULT_CHARS", "4000"))

YES = re.compile(r"^\s*(y|yes|yep|yeah|ok|okay|sure|confirm|confirmed|go ahead|do it|oui|ouais|vas-y|d'accord|"
                 r"confirme|sí|si|vale)\b[\s.!]*$", re.I)
NO = re.compile(r"^\s*(n|no|nope|cancel|stop|don't|do not|non|annule|annuler|pas question|no gracias)\b[\s.!]*$", re.I)
UNDO = re.compile(r"^\s*(undo|revert|undo (that|it|last( change)?)|annule(r)?( ça| la dernière modification)?|"
                  r"deshacer)\s*[.!]*\s*$", re.I)
CHECK = re.compile(r"^\s*(check|validate|verify|vérifie|valide)\s+(?P<target>[\w./-]+\.ya?ml)\s*[.!?]*\s*$", re.I)

SYSTEM_PROMPT = """You are Hyperion Steward, the assistant inside the HYPER-AI IDE.
You answer questions about HYPER-AI and you act in the user's workspace through tools.

Your promise: you never leave the workspace worse than you found it.

Rules:
- For any question about HYPER-AI, the IDE, the DSL or deployment, call search_docs first and answer only from
  the returned passages. Cite sources as [n] using the numbers returned. If the docs do not cover it, say so.
- To create a NEW profile, prefer create_profile: give the parameters you know (name, workload, image, ports,
  latency, architectures...) and it builds a complete, spec-correct profile, then writes and validates it.
  Tell the user which values were defaults so they can change them.
- To change an existing profile, read_file it, then call write_profile with the full edited YAML. It checks the profile
  locally, writes it, asks the IDE validator, and rolls back automatically if the validator rejects it.
  Never say a profile is valid unless write_profile or validate_file reported valid=true.
- Before writing, draft complete profiles that satisfy the DSL: Native apps use `applicationProfile:`;
  Device apps use `apiVersion: hyper.ai/v1` and `kind: Application`. Use search_docs for field details.
- When a tool returns status "ambiguous", list the matching paths and ask which one. Never guess.
- When a tool returns "needs_confirmation", ask the user a clear yes/no question and stop.
- Report runnability findings honestly: a schema-valid profile can still fail to run.
- If a tool result has effect "not_seen", the IDE has not applied the change yet: say so, never claim it is done.
- To change an existing file, read_file it first. Use full paths once you know them.
- Paths are relative to the workspace root. Never use absolute paths or "..".
- Never paste a profile into the chat as a proposal. Change files only through tools; to change a few fields of an
  existing profile, use edit_profile.
- When the user asks you to create or change something, do it now with your tools. Do not ask "would you like
  me to...?" first. Steward itself asks the user whenever a confirmation is needed.
- You cannot deploy or start workflows; tell the user to use the IDE's Deploy and Start buttons.
- Be brief. Plain text only: the IDE panel does not render markdown, so no **, no backticks, no # headings.
  Short lines and simple dashes for lists are fine. Do not narrate tool mechanics.
"""

TOOLS: list[dict[str, Any]] = [
    {"name": "search_docs", "description": "Search the official HYPER-AI documentation. Returns numbered passages with sources.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "read_file", "description": "Read a workspace file by full path or bare name. Returns content, or matches if ambiguous.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "validate_file", "description": "Check an existing profile file: IDE validator result plus runnability verdict. Use this to answer 'will this file run?'.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "check_profile", "description": "Check YAML text locally (spec rules + runnability) without writing anything.",
     "input_schema": {"type": "object", "properties": {"yaml": {"type": "string", "description": "YAML text, or a workspace .yaml path"}}, "required": ["yaml"]}},
    {"name": "create_profile",
     "description": "Build a complete new profile from parameters and write it safely. kind=device (Docker image, "
                    "Android APK or ESP32 firmware on edge devices) or kind=native (container/VM on the continuum).",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string", "description": "workspace-relative .yaml path"},
         "kind": {"type": "string", "enum": ["device", "native"]},
         "name": {"type": "string"},
         "workload": {"type": "string", "enum": ["DockerImage", "AndroidApk", "esp32Binary"],
                      "description": "device only"},
         "image": {"type": "string", "description": "container image, e.g. acme/api:1.2"},
         "entry_point": {"type": "string", "description": "native only: command the container runs"},
         "args": {"type": "array", "items": {"type": "string"}},
         "apk_url": {"type": "string"}, "package_name": {"type": "string"},
         "binary_url": {"type": "string"}, "chip": {"type": "string"},
         "device_name": {"type": "string"},
         "architectures": {"type": "array", "items": {"type": "string"}},
         "ports": {"type": "array", "items": {"type": "integer"}},
         "latency_ms": {"type": "number"},
         "availability": {"type": "number", "description": "device: fraction 0-1; native: percent"},
         "lifecycle_phase": {"type": "string", "enum": ["development", "testing", "production"]},
         "description": {"type": "string"},
         "public": {"type": "boolean", "description": "native only: expose ports publicly"}},
         "required": ["path", "kind", "name"]}},
    {"name": "write_profile", "description": "Create or update a .yaml application profile safely (local check, write, IDE validation, auto-rollback).",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "yaml": {"type": "string"}},
                      "required": ["path", "yaml"]}},
    {"name": "edit_profile",
     "description": "Change a few fields of an existing profile. changes maps dotted field paths to new values, e.g. "
                    "{\"specs.runtime.containerImage.uri\": \"acme/api\", \"specs.network.ports[0].port\": 8000}. "
                    "Same safety path as write_profile. Prefer this to rewriting the whole file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "changes": {"type": "object"}},
                      "required": ["path", "changes"]}},
    {"name": "write_file", "description": "Create or update a non-profile text file (README, notes, scripts).",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "create_folder", "description": "Create a folder in the workspace.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "delete_file", "description": "Request deletion of a file. Resolves the exact file and asks the user to confirm.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "delete_folder", "description": "Request deletion of a folder. Always asks the user to confirm; not reversible.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "undo", "description": "Revert the most recent change Steward made in this session.",
     "input_schema": {"type": "object", "properties": {}}},
]


class Steward:
    def __init__(self, ide: IdeClient, docs: DocsIndex, llm: LLM | None):
        self.ide = ide
        self.docs = docs
        self.llm = llm

    async def handle(self, session: Session, text: str, ops: SafeOps) -> None:
        started = time.perf_counter()
        session.receipt("user", text=text[:500])
        ops.explicit_targets = set(re.findall(r"[\w.-]+(?:/[\w.-]+)+\.ya?ml|[\w.-]+(?:/[\w.-]+)+\.\w+", text))
        try:
            if session.pending is not None:
                if YES.match(text):
                    await self._report_tool(ops, "confirmation", await ops.resolve_pending(True))
                    return
                if NO.match(text):
                    await self._report_tool(ops, "confirmation", await ops.resolve_pending(False))
                    return
                session.receipt("guard", rule="I4", decision="pending_cleared_by_new_request",
                                path=session.pending.path)
                await ops.say(f"(I've cancelled the pending request to {session.pending.summary}.) ")
                session.pending = None
            if UNDO.match(text):
                await self._report_tool(ops, "undo", await ops.undo())
                return
            match = CHECK.match(text)
            if match:
                await self._check_command(ops, match.group("target"))
                return
            verdict = guardrail.classify(text, self.docs, in_conversation=bool(session.history))
            session.receipt("guardrail", in_scope=verdict.in_scope, reason=verdict.reason)
            if not verdict.in_scope:
                await ops.say(guardrail.REFUSAL)
                return
            intent = intents.parse(text)
            if intent is not None:
                # Unambiguous action requests run deterministically even when a model is available: faster on the
                # 8B model, and no chance of the model asking needless questions or inventing YAML (D-031).
                session.receipt("intent_route", intent=intent.kind, args=dict(intent.args))
                await self._run_intent(ops, intent)
                self._remember(session, text, ops)
                return
            if self.llm is None:
                await self._degraded(ops, text, reason="no language model is configured")
                return
            if YES.match(text) or NO.match(text):
                text = (f"{text}\n\n(Steward note: nothing was waiting for confirmation. If your previous message "
                        "proposed a change, make it now with edit_profile, write_profile or create_profile; do not "
                        "ask again.)")
            await self._llm_turn(session, text, ops)
        finally:
            session.receipt("turn_done", latency_ms=int((time.perf_counter() - started) * 1000))

    # -- deterministic paths ----------------------------------------------------------------------

    async def _check_command(self, ops: SafeOps, target: str) -> None:
        res = await ops.resolve(target)
        if res.status == "ambiguous":
            await ops.say(_ambiguity_text(target, res.matches))
            return
        if res.status != "resolved":
            await ops.say(_unresolved_text(target, res.status, res.detail))
            return
        report = await ops.validate(res.path)
        run = runnability.assess(res.content or "")
        await ops.say(_check_text(res.path, report, run))

    async def _report_tool(self, ops: SafeOps, tool: str, result: dict[str, Any]) -> None:
        await ops.say(_result_text(tool, result))

    async def _degraded(self, ops: SafeOps, text: str, reason: str) -> None:
        ops.s.receipt("degraded_mode", reason=reason)
        intent = intents.parse(text)
        if intent is not None:
            ops.s.receipt("intent_fallback", intent=intent.kind, args={k: v for k, v in intent.args.items()})
            await self._run_intent(ops, intent)
            return
        hits = self.docs.search(text, k=2)
        if hits:
            parts = [f"My language model is unavailable right now ({reason}), so here is the closest part of the "
                     "HYPER-AI docs:\n\n"]
            for i, (_, chunk) in enumerate(hits, 1):
                excerpt = chunk.text.strip().replace("\n", " ")
                parts.append(f"[{i}] **{chunk.heading}**: {excerpt[:600]}\n\n")
            parts.append("Sources: " + "; ".join(f"[{i}] {c.citation}" for i, (_, c) in enumerate(hits, 1)))
            parts.append("\n\n" + _DEGRADED_CAN_DO)
            await ops.say("".join(parts))
        else:
            await ops.say(f"My language model is unavailable right now ({reason}). " + _DEGRADED_CAN_DO)

    async def _edit_profile(self, ops: SafeOps, target: str, changes: dict[str, Any]) -> dict[str, Any]:
        res = await ops.resolve(target)
        if res.status != "resolved":
            return {"status": res.status, "matches": res.matches, "reason": res.detail}
        try:
            new_text, changed = patching.apply_changes(res.content or "", changes)
        except patching.PatchError as exc:
            return {"status": "needs_input", "detail": str(exc)}
        if not changed:
            return {"status": "unchanged", "path": res.path}
        ops.s.receipt("edit_profile", path=res.path, fields=changed)
        ops.explicit_targets.add(res.path)  # the user asked for these exact fields to change; a restore point is kept
        result = await ops.write_profile(res.path, new_text)
        result["fields_changed"] = changed
        result["changes"] = {patching.normalise_path({"applicationProfile": 1} if k.startswith(("specs.", "metadata."))
                                                     and "applicationProfile" in (res.content or "") else {}, k): v
                             for k, v in changes.items()}
        return result

    async def _run_intent(self, ops: SafeOps, intent: intents.Intent) -> None:
        if intent.kind == "fix_profile":
            res = await ops.resolve(intent.args["path"])
            if res.status == "ambiguous":
                await ops.say(_ambiguity_text(intent.args["path"], res.matches))
                return
            if res.status != "resolved":
                await ops.say(_unresolved_text(intent.args["path"], res.status, res.detail))
                return
            doc, _ = spec.parse_profile(res.content or "")
            changes = intents.fix_changes(doc, intent.args)
            result = await self._edit_profile(ops, res.path, changes)
            await ops.say(_edited_text(result))
            return
        if intent.kind == "create_profile":
            result = await self._create_profile(ops, intent.args)
            await ops.say(_created_text(intent.args, result))
        elif intent.kind == "delete":
            result = await ops.request_delete(intent.args["path"])
            message = _guard_message(intent.args, result)
            if not message:
                message = _unresolved_text(intent.args["path"], str(result.get("status")), str(result.get("reason", "")))
            await ops.say(message)
        elif intent.kind == "create_folder":
            result = await ops.create_folder(intent.args["path"])
            if result.get("status") != "created":
                await ops.say(f"I can't use that path: {result.get('reason')}")
            elif result.get("effect") != "verified":
                await ops.say(_unconfirmed_text({"status": "sent_unverified", "path": result["path"]}))
            else:
                await ops.say(f"Created folder {result['path']}. Say undo to remove it.")

    # -- model-driven path ------------------------------------------------------------------------


    def _docs_block(self, session: Session, text: str) -> str:
        """Retrieval by default: the most relevant official passages go into context on every turn, so answers
        stay grounded even when the model forgets to call search_docs."""
        hits = self.docs.search(text, k=2, min_score=2.5)
        if not hits:
            return ""
        session.receipt("docs_prefetch", hits=[c.citation for _, c in hits])
        lines = ["\n\nRelevant official HYPER-AI documentation for this message (cite as [D1], [D2]...; "
                 "answer from these when the user asks about HYPER-AI or the IDE):"]
        for i, (_, chunk) in enumerate(hits, 1):
            lines.append(f"[D{i}] {chunk.citation}\n{chunk.text[:900]}")
        return "\n\n".join(lines)

    async def _llm_turn(self, session: Session, text: str, ops: SafeOps) -> None:
        assert self.llm is not None
        system = SYSTEM_PROMPT + _context_block(session) + self._docs_block(session, text)
        messages = [*session.history, {"role": "user", "content": text}]
        final_text: list[str] = []
        actions_before = len(session.journal)
        for step in range(MAX_STEPS):
            trimmed = _fit_context(system, messages)
            if trimmed:
                session.receipt("context_trim", dropped_messages=trimmed, budget_tokens=CONTEXT_TOKENS)
            try:
                turn: LLMTurn = await self.llm.step(system, messages, TOOLS, on_text=ops.say)
            except LLMError as exc:
                session.receipt("llm_error", error=str(exc)[:300], step=step)
                await self._degraded(ops, text, reason="the model call failed")
                return
            session.receipt("llm", model=turn.model, step=step, input_tokens=turn.input_tokens,
                            output_tokens=turn.output_tokens, latency_ms=turn.latency_ms,
                            tools=[c.name for c in turn.tool_calls])
            if turn.text:
                final_text.append(turn.text)
            messages.append({"role": "assistant", "content": turn.raw_content})
            if not turn.tool_calls:
                break
            results = []
            stop = False
            for call in turn.tool_calls:
                output = await self._run_tool(ops, call.name, call.input)
                guard_text = _guard_message(call.input, output)
                if guard_text:
                    # Safety questions are part of the product, not something the model may forget to say.
                    await ops.say(("\n\n" if final_text else "") + guard_text)
                    final_text.append(guard_text)
                    output = {**output, "already_told_user": guard_text,
                              "instruction": "The user has been asked. Do not repeat the question; end your turn."}
                    stop = True
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": _clip_result(output)})
            messages.append({"role": "user", "content": results})
            if stop:
                break
        else:
            await ops.say("\n\n(I stopped after several steps to avoid looping. Tell me how to continue.)")
        changed = [f"{e.action} {e.path}" for e in session.journal[actions_before:]]
        summary = "".join(final_text).strip()
        if changed:
            summary += "\n[workspace changes this turn: " + "; ".join(changed) + "]"
        session.history.extend([{"role": "user", "content": text},
                                {"role": "assistant", "content": summary or "(no text)"}])
        del session.history[:-24]


    @staticmethod
    def _remember(session: Session, text: str, ops: SafeOps) -> None:
        """Deterministic turns still go into session memory, so a later model turn knows what happened."""
        said = " ".join(ops.spoken).strip()
        session.history.extend([{"role": "user", "content": text}, {"role": "assistant", "content": said or "(done)"}])
        del session.history[:-24]

    async def _create_profile(self, ops: SafeOps, args: dict[str, Any]) -> dict[str, Any]:
        kind = str(args.get("kind", "")).lower()
        try:
            if kind == "device":
                availability = args.get("availability")
                yaml_text = templates.build_device_profile(
                    name=str(args.get("name")), workload=str(args.get("workload") or "DockerImage"),
                    image=args.get("image"), apk_url=args.get("apk_url"), package_name=args.get("package_name"),
                    binary_url=args.get("binary_url"), chip=args.get("chip"), device_name=args.get("device_name"),
                    architectures=args.get("architectures"), ports=args.get("ports"),
                    latency_ms=float(args.get("latency_ms") or 500),
                    availability=float(availability) / 100 if availability and float(availability) > 1
                    else float(availability or 0.9),
                    lifecycle_phase=str(args.get("lifecycle_phase") or "development"),
                    description=args.get("description"))
            elif kind == "native":
                if not args.get("image"):
                    return {"status": "needs_input", "missing": ["image"]}
                yaml_text = templates.build_native_profile(
                    name=str(args.get("name")), image=str(args.get("image")), entry_point=args.get("entry_point"),
                    args=args.get("args"), ports=args.get("ports"), public=bool(args.get("public", False)),
                    architectures=args.get("architectures"), latency_ms=args.get("latency_ms"),
                    availability_percent=args.get("availability"),
                    lifecycle_phase=str(args.get("lifecycle_phase") or "development"),
                    description=args.get("description"))
            else:
                return {"status": "needs_input", "missing": ["kind (device|native)"]}
        except (ValueError, TypeError) as exc:
            return {"status": "needs_input", "detail": str(exc)}
        ops.s.receipt("create_profile", profile_kind=kind, path=args.get("path"))
        result = await ops.write_profile(str(args.get("path", "")), yaml_text)
        result["generated_yaml"] = yaml_text
        result["note"] = "Built from parameters; unspecified fields use cookbook-aligned defaults visible in the YAML."
        return result

    async def _run_tool(self, ops: SafeOps, name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "search_docs":
                hits = self.docs.search(str(args.get("query", "")), k=4)
                ops.s.receipt("search_docs", query=args.get("query"), hits=[c.citation for _, c in hits])
                if not hits:
                    return {"status": "no_results", "note": "The official docs corpus has nothing on this."}
                return {"status": "ok", "passages": [
                    {"n": i, "source": c.citation, "fidelity": c.fidelity, "text": c.text[:1500]}
                    for i, (_, c) in enumerate(hits, 1)]}
            if name == "read_file":
                res = await ops.resolve(str(args.get("path", "")))
                return {"status": res.status, "path": res.path, "content": res.content, "matches": res.matches,
                        "detail": res.detail}
            if name == "validate_file":
                res = await ops.resolve(str(args.get("path", "")))
                if res.status != "resolved":
                    return {"status": res.status, "matches": res.matches, "detail": res.detail}
                report = await ops.validate(res.path)
                return {"status": report.outcome.value, "path": res.path, "valid": report.valid,
                        "errors": report.errors, "warnings": report.warnings,
                        "runnability": runnability.assess(res.content or "").as_dict()}
            if name == "check_profile":
                text = str(args.get("yaml", "") or args.get("path", ""))
                if "\n" not in text and text.strip().endswith((".yaml", ".yml")):
                    res = await ops.resolve(text.strip())  # the model passed a file path, not YAML text
                    if res.status != "resolved":
                        return {"status": res.status, "matches": res.matches, "detail": res.detail}
                    text = res.content or ""
                local = spec.check_profile(text)
                return {"status": "ok", "kind": local.kind.value, "parse_error": local.parse_error,
                        "issues": [i.as_dict() for i in local.issues],
                        "runnability": runnability.assess(text).as_dict(),
                        "note": "Local check only; the IDE validator is authoritative."}
            if name == "create_profile":
                return await self._create_profile(ops, args)
            if name == "write_profile":
                return await ops.write_profile(str(args.get("path", "")), str(args.get("yaml", "")))
            if name == "edit_profile":
                changes = args.get("changes")
                if not isinstance(changes, dict) or not changes:
                    return {"status": "needs_input", "detail": "changes must map field paths to values"}
                return await self._edit_profile(ops, str(args.get("path", "")), changes)
            if name == "write_file":
                return await ops.write_text_file(str(args.get("path", "")), str(args.get("content", "")))
            if name == "create_folder":
                return await ops.create_folder(str(args.get("path", "")))
            if name == "delete_file":
                return await ops.request_delete(str(args.get("path", "")))
            if name == "delete_folder":
                return await ops.request_delete_folder(str(args.get("path", "")))
            if name == "undo":
                return await ops.undo()
            return {"status": "unknown_tool", "tool": name}
        except Exception as exc:  # a tool bug must not crash the stream or emit half an action
            ops.s.receipt("tool_error", tool=name, error=f"{type(exc).__name__}: {exc}"[:300])
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:300]}


# -- text helpers -----------------------------------------------------------------------------------

def _estimate_tokens(obj: Any) -> int:
    return int(len(json.dumps(obj, ensure_ascii=False)) / 3.5)


TOOLS_TOKENS = _estimate_tokens(TOOLS)


def _fit_context(system: str, messages: list[dict[str, Any]]) -> int:
    """Drop the oldest history until the request fits the model context. Never drops the current user message or
    the in-flight tool exchange. Returns how many messages were dropped."""
    budget = CONTEXT_TOKENS - OUTPUT_TOKENS - TOOLS_TOKENS - 200
    dropped = 0
    while _estimate_tokens(system) + _estimate_tokens(messages) > budget and len(messages) > 1:
        first = messages[0]
        if first["role"] == "user" and not isinstance(first["content"], str):
            break  # a tool_result block belongs to the in-flight exchange
        if any(isinstance(m["content"], list) for m in messages[:2]) and dropped == 0 and len(messages) <= 3:
            break
        messages.pop(0)
        dropped += 1
        while messages and messages[0]["role"] != "user":  # keep history starting on a user turn
            messages.pop(0)
            dropped += 1
    return dropped


def _clip_result(output: dict[str, Any]) -> str:
    text = json.dumps(output, ensure_ascii=False)
    if len(text) <= TOOL_RESULT_CHARS:
        return text
    return text[:TOOL_RESULT_CHARS] + f'... [truncated {len(text) - TOOL_RESULT_CHARS} chars to fit the model context]'


def _context_block(session: Session) -> str:
    lines = []
    if session.known_paths:
        lines.append("Files touched or read in this session (most recent last): " + ", ".join(session.known_paths[-10:]))
    if session.created_paths:
        lines.append("Files you created in this session: " + ", ".join(sorted(session.created_paths)))
    undoable = [e for e in session.journal if not e.undone]
    if undoable:
        last = undoable[-1]
        lines.append(f"Last reversible change: {last.action} {last.path}")
    return ("\n\nSession context:\n" + "\n".join(lines)) if lines else ""


def _guard_message(args: dict[str, Any], output: dict[str, Any]) -> str:
    status = output.get("status")
    if status == "ambiguous":
        target = str(args.get("path", "that name"))
        return _ambiguity_text(target, output.get("matches") or [])
    if status == "needs_confirmation":
        path = output.get("path", "")
        if output.get("reversible") is False:
            return f"Delete the folder `{path}` and everything in it? This can't be undone. Reply **yes** or **no**."
        if "size" in output:
            return f"Delete `{path}`? I'll keep a copy so you can `undo`. Reply **yes** or **no**."
        return (f"`{path}` already exists and I didn't create it in this session. Overwrite it? "
                "I'll keep a copy so you can `undo`. Reply **yes** or **no**.")
    return ""


def _ambiguity_text(target: str, matches: list[str]) -> str:
    listed = "\n".join(f"- `{m}`" for m in matches)
    return (f"There are {len(matches)} files named `{target}`, so I didn't touch any of them. "
            f"Which one do you mean?\n{listed}")


def _unresolved_text(target: str, status: str, detail: str) -> str:
    if status == "missing":
        return f"I couldn't find `{target}` in the workspace."
    if status == "invalid":
        return f"I can't use that path: {detail}"
    return f"I couldn't reach the IDE backend to look up `{target}` ({detail}). I didn't change anything."


_DEGRADED_CAN_DO = ("Without the model I can still create a profile from a simple request (for example: create a "
                    "deployment YAML for the nginx Docker image), delete a file with your confirmation, create a "
                    "folder, check <file>.yaml, and undo my last change.")


def _edited_text(r: dict[str, Any]) -> str:
    status, path = r.get("status"), r.get("path")
    if status in ("sent_unverified",) or r.get("effect") in ("not_seen", "unobservable"):
        return _unconfirmed_text({"status": "sent_unverified", "path": path})
    if status == "written_valid":
        values = r.get("changes") or {}
        fields = ", ".join(f"{f.replace('applicationProfile.', '')} = {values.get(f, '?')}"
                           for f in r.get("fields_changed", []))
        run = r.get("runnability") or {}
        verdict = {"will_not_run": "still will not run as written", "at_risk": "no blocker left, some risks",
                   "no_known_blocker": "no known blocker"}.get(run.get("verdict"), "not assessed")
        notes = "".join(f"\n- {f['message']}" for f in run.get("findings", [])[:3])
        return (f"Updated {path} ({fields}). The IDE validator reports it valid. Runnability: {verdict}.{notes}\n"
                "Say undo to restore the previous version.")
    if status == "unchanged":
        return f"{path} already has those values; nothing to change."
    if status == "local_check_failed":
        errs = "; ".join(f"{i['field']}: {i['message']}" for i in r.get("issues", [])[:4])
        return f"That change would make {path} invalid ({errs}), so I didn't write it."
    if status == "rolled_back_invalid":
        return _result_text("write_profile", r)
    return f"I couldn't update {path} ({status}: {r.get('detail') or r.get('reason') or ''})."


def _created_text(args: dict[str, Any], r: dict[str, Any]) -> str:
    status = r.get("status")
    path = r.get("path") or args.get("path")
    if status in ("needs_confirmation", "ambiguous"):
        return _guard_message(args, r)
    if status == "sent_unverified" or r.get("effect") in ("not_seen", "unobservable"):
        return _unconfirmed_text({"status": "sent_unverified", "path": path})
    if status == "written_valid":
        bits = [f"{args.get('kind', 'device')} profile for the image {args.get('image')}"]
        if args.get("ports"):
            bits.append(f"port {', '.join(str(p) for p in args['ports'])}")
        verdict = (r.get("runnability") or {}).get("verdict")
        tail = " Runnability: will not run as written; ask me to check it." if verdict == "will_not_run" else ""
        return (f"Created {path} ({', '.join(bits)}) and opened it in the editor. The IDE validator reports it valid. "
                "Fields I wasn't told (owner, QoS, resources) use defaults you can see and edit in the file. "
                f"Say undo to remove it.{tail}")
    if status == "rolled_back_invalid":
        return _result_text("write_profile", r)
    if status == "blocked":
        return f"I couldn't reach the IDE backend, so I didn't create {path}."
    return f"I couldn't create {path} ({status})."


def _unconfirmed_text(r: dict[str, Any]) -> str:
    what = {"deleted": "the delete of", "deleted_folder": "the folder delete of", "undone": "the undo of",
            "sent_unverified": "the change to"}.get(str(r.get("status")), "the change to")
    return (f"I sent {what} `{r.get('path')}` to the IDE, but it hasn't shown up in the workspace yet, so I can't "
            "confirm it happened. Is the IDE open in your browser? Check the file tree, or ask me to check again.")


def _check_text(path: str, report: Any, run: runnability.RunnabilityReport) -> str:
    out = [f"**{path}**"]
    if report.outcome.value == "ok":
        if report.valid:
            out.append("IDE validator: **valid**.")
        else:
            errs = "; ".join(f"line {e.get('line')}: {e.get('field')} {e.get('message')}" for e in report.errors[:6])
            out.append(f"IDE validator: **invalid** — {errs}.")
    else:
        out.append(f"IDE validator: not checked ({report.outcome.value}).")
    if run.verdict is runnability.Verdict.WILL_NOT_RUN:
        out.append("Runnability: **will not run as written**.")
    elif run.verdict is runnability.Verdict.AT_RISK:
        out.append("Runnability: at risk.")
    elif run.verdict is runnability.Verdict.NO_KNOWN_BLOCKER:
        out.append("Runnability: no known blocker.")
    for f in run.findings:
        out.append(f"- {f.message} Fix: {f.fix}")
    return "\n".join(out)


def _result_text(tool: str, r: dict[str, Any]) -> str:
    status = r.get("status")
    if r.get("effect") in ("not_seen", "unobservable") or status == "sent_unverified":
        return _unconfirmed_text(r)
    if tool == "undo":
        if status == "undone":
            return f"Undone: reverted `{r['action']}` on `{r['path']}`."
        if status == "not_reversible":
            return f"The last change (`{r['action']}` on `{r['path']}`) can't be undone automatically."
        return "There's nothing of mine to undo in this session."
    if status == "cancelled":
        return f"Cancelled. I left `{r['path']}` untouched."
    if status == "deleted":
        return f"Deleted `{r['path']}`. Say `undo` to bring it back."
    if status == "deleted_folder":
        return f"Deleted folder `{r['path']}`."
    if status == "stale":
        return f"`{r['path']}` changed or disappeared since you confirmed ({r.get('detail')}), so I didn't act."
    if status in ("written_valid", "written"):
        return f"Saved `{r['path']}`" + (" — the IDE validator reports it valid." if status == "written_valid" else ".")
    if status == "rolled_back_invalid":
        errs = "; ".join(f"{e.get('field')}: {e.get('message')}" for e in r["validator"]["errors"][:5])
        return f"The IDE validator rejected it ({errs}), so I restored `{r['path']}` to how it was."
    if status == "nothing_pending":
        return "There was nothing waiting for confirmation."
    return f"Result: {status}."
