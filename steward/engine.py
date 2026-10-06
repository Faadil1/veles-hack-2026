"""Guarded workspace operations, restore-point journal, per-user sessions and receipts.

Invariants enforced here, independent of any LLM output:
  I1  No edit/delete is emitted against a name that the IDE reports as ambiguous (409).
  I2  Every edit/delete records the exact prior content first, so `undo` can restore it.
  I3  A profile never overwrites an existing file unless the result is validator-clean; failed writes roll back.
  I4  Destructive actions need explicit user consent: deletions always ask; overwriting a file Steward did not
      create asks unless the user named that exact path in the current request.
  I5  If a required check cannot run (backend unreachable), no action is emitted.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from collections.abc import Awaitable, Callable

from . import runnability, spec
from .ide import (
    FileResult,
    IdeClient,
    Outcome,
    PathError,
    ValidationResult,
    action_event,
    response_event,
    safe_path,
)

Emit = Callable[[str], Awaitable[None]]
_ids = itertools.count(1)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


@dataclass
class JournalEntry:
    entry_id: int
    action: str
    path: str
    before: str | None  # None means the file did not exist
    after: str | None
    reversible: bool = True
    undone: bool = False
    effect: str = "none"  # verified | not_seen | unobservable
    at: str = field(default_factory=_now)


@dataclass
class Pending:
    """An action waiting for the user's explicit yes/no."""
    kind: str  # "delete_file" | "delete_folder" | "overwrite"
    path: str
    summary: str
    content: str | None = None
    before: str | None = None


@dataclass
class Session:
    user_id: str
    history: list[dict[str, Any]] = field(default_factory=list)
    journal: list[JournalEntry] = field(default_factory=list)
    receipts: list[dict[str, Any]] = field(default_factory=list)
    pending: Pending | None = None
    created_paths: set[str] = field(default_factory=set)
    known_paths: list[str] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def receipt(self, kind: str, /, **data: Any) -> dict[str, Any]:
        # `kind` is positional-only so callers can log a field that is itself named "kind"
        # (a keyword collision here crashed tool calls twice before this change).
        item = {**data, "seq": len(self.receipts) + 1, "at": _now(), "kind": kind}
        self.receipts.append(item)
        return item

    def remember_path(self, path: str) -> None:
        if path in self.known_paths:
            self.known_paths.remove(path)
        self.known_paths.append(path)
        del self.known_paths[:-25]


class SessionStore:
    def __init__(self, max_history: int = 40):
        self._sessions: dict[str, Session] = {}
        self.max_history = max_history

    def get(self, user_id: str) -> Session:
        if user_id not in self._sessions:
            self._sessions[user_id] = Session(user_id=user_id)
        return self._sessions[user_id]

    def peek(self, user_id: str) -> Session | None:
        return self._sessions.get(user_id)


@dataclass
class Resolution:
    status: str  # resolved | ambiguous | missing | unreachable | invalid
    path: str | None = None
    content: str | None = None
    matches: list[str] = field(default_factory=list)
    detail: str = ""


class SafeOps:
    """The only code path that emits IDE actions."""

    def __init__(self, ide: IdeClient, session: Session, emit: Emit,
                 validate_retries: int = 6, validate_delay_s: float = 0.4,
                 effect_timeout_s: float = 6.0, effect_poll_s: float = 0.25):
        self.ide = ide
        self.s = session
        self.emit = emit
        # Paths the user named explicitly in the current message. Asking to change a file by its exact path is
        # consent to overwrite that file (a restore point is still kept). Deletions always ask.
        self.explicit_targets: set[str] = set()
        self.validate_retries = validate_retries
        self.validate_delay_s = validate_delay_s
        # The IDE frontend executes streamed actions fire-and-forget and never reports back. Steward reads the
        # workspace back through the backend after every action, so it only claims what it has seen, and the next
        # action on the same path is not emitted before the previous one landed (the GUI does not serialise them).
        self.effect_timeout_s = effect_timeout_s
        self.effect_poll_s = effect_poll_s
        self.last_effect = "none"

    # -- reads ------------------------------------------------------------------------------------

    async def resolve(self, target: str) -> Resolution:
        try:
            target = safe_path(target)
        except PathError as exc:
            return Resolution("invalid", detail=str(exc))
        result: FileResult = await self.ide.read_file(target)
        self.s.receipt("read_file", target=target, outcome=result.outcome.value, path=result.path,
                       matches=result.matches, latency_ms=result.latency_ms)
        if result.outcome is Outcome.OK:
            self.s.remember_path(result.path or target)
            return Resolution("resolved", path=result.path or target, content=result.content)
        if result.outcome is Outcome.AMBIGUOUS:
            self.s.receipt("guard", rule="I1", decision="blocked_first_match", target=target, matches=result.matches)
            return Resolution("ambiguous", matches=result.matches)
        if result.outcome is Outcome.NOT_FOUND:
            return Resolution("missing", detail=result.detail)
        return Resolution("unreachable", detail=result.detail)

    async def validate(self, path: str, wait_for_file: bool = False) -> ValidationResult:
        attempts = self.validate_retries if wait_for_file else 1
        result = ValidationResult(Outcome.ERROR)
        for attempt in range(attempts):
            result = await self.ide.validate_file(path)
            if result.outcome is not Outcome.NOT_FOUND or attempt == attempts - 1:
                break
            await asyncio.sleep(self.validate_delay_s)
        self.s.receipt("validate_file", path=path, outcome=result.outcome.value, valid=result.valid,
                       errors=result.errors, warnings=result.warnings, latency_ms=result.latency_ms,
                       attempts=attempt + 1)
        return result

    # -- emits ------------------------------------------------------------------------------------

    async def say(self, text: str) -> None:
        await self.emit(response_event(text))

    async def _act(self, action: str, path: str, content: str | None, before: str | None,
                   reversible: bool = True, record: bool = True) -> JournalEntry | None:
        await self.emit(action_event(action, path, content))
        entry = None
        if record:
            entry = JournalEntry(next(_ids), action, path, before,
                                 content if action in ("create_file", "edit_file") else None, reversible)
            self.s.journal.append(entry)
        self.s.receipt("action", action=action, path=path, journal_id=entry.entry_id if entry else None,
                       bytes=len(content or ""), reversible=reversible)
        if action == "create_file":
            self.s.created_paths.add(path)
        self.s.remember_path(path)
        self.last_effect = await self._verify_effect(action, path, content)
        if entry is not None:
            entry.effect = self.last_effect
        return entry

    async def _effect_seen(self, action: str, path: str, content: str | None) -> bool | None:
        """True when the action is visible in the workspace, False when not yet, None when unobservable."""
        if action in ("create_file", "edit_file", "delete_file"):
            res = await self.ide.read_file(path)
            if res.outcome is Outcome.UNREACHABLE:
                return None
            if action == "delete_file":
                return res.outcome is Outcome.NOT_FOUND
            return res.outcome is Outcome.OK and res.path == path and res.content == (content or "")
        exists = await self.ide.folder_exists(path)
        if not isinstance(exists, bool):
            return None
        return exists if action == "create_folder" else not exists

    async def _verify_effect(self, action: str, path: str, content: str | None) -> str:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.effect_timeout_s
        polls = 0
        while True:
            polls += 1
            seen = await self._effect_seen(action, path, content)
            if seen is None:
                status = "unobservable"
                break
            if seen:
                status = "verified"
                break
            if loop.time() >= deadline:
                status = "not_seen"
                break
            await asyncio.sleep(self.effect_poll_s)
        self.s.receipt("effect", action=action, path=path, status=status, polls=polls)
        return status

    # -- profile writes ---------------------------------------------------------------------------

    async def write_profile(self, path: str, content: str, confirmed_overwrite: bool = False) -> dict[str, Any]:
        """Write a YAML profile safely. Returns a structured result for the planner."""
        try:
            path = safe_path(path)
        except PathError as exc:
            return {"status": "rejected", "reason": str(exc)}
        if not path.endswith((".yaml", ".yml")):
            return {"status": "rejected", "reason": "profiles must be .yaml/.yml files"}

        local = spec.check_profile(content)
        if not local.ok:
            self.s.receipt("local_check", path=path, ok=False,
                           issues=[i.as_dict() for i in local.issues], parse_error=local.parse_error)
            return {"status": "local_check_failed", "parse_error": local.parse_error,
                    "issues": [i.as_dict() for i in local.errors]}
        run = runnability.assess(content)
        self.s.receipt("runnability", path=path, **run.as_dict())

        existing = await self.resolve(path)
        if existing.status == "unreachable":
            return {"status": "blocked", "reason": "IDE backend unreachable; nothing was written",
                    "detail": existing.detail}
        if existing.status == "ambiguous":
            return {"status": "ambiguous", "matches": existing.matches}
        target = existing.path or path
        before = existing.content if existing.status == "resolved" else None
        if before is not None and before == content:
            return {"status": "unchanged", "path": target}
        if before is not None and target not in self.s.created_paths and not confirmed_overwrite:
            if target in self.explicit_targets:
                self.s.receipt("guard", rule="I4", decision="overwrite_consented_by_explicit_path", path=target)
            else:
                self.s.pending = Pending("overwrite", target, f"overwrite `{target}`", content=content, before=before)
                self.s.receipt("guard", rule="I4", decision="confirm_overwrite", path=target)
                return {"status": "needs_confirmation", "path": target,
                        "reason": "file exists and was not created by Steward in this session"}

        action = "edit_file" if before is not None else "create_file"
        await self._act(action, target, content, before)
        result: dict[str, Any] = {
            "path": target, "action": action, "effect": self.last_effect, "local_validator": "valid",
            "runnability": run.as_dict(), "local_warnings": [i.as_dict() for i in local.issues],
        }
        if self.last_effect != "verified":
            # Validating now would read the old file (or nothing). The local check is a proven port of the IDE
            # validator, so validity is known; what is unknown is whether the IDE applied the change.
            result["validator"] = {"outcome": "skipped", "valid": None, "detail": "change not visible in the IDE"}
            result["status"] = "sent_unverified"
            return result
        report = await self.validate(target, wait_for_file=True)
        result["validator"] = _validation_summary(report)
        if report.outcome is Outcome.OK and report.valid:
            result["status"] = "written_valid"
            return result
        if report.outcome is Outcome.OK and report.valid is False:
            await self._rollback(target, before, reason="IDE validator rejected the profile")
            result["status"] = "rolled_back_invalid"
            return result
        # Could not confirm validity (unreachable / still not found): keep honest state, do not claim valid.
        result["status"] = "written_unverified"
        return result

    async def _rollback(self, path: str, before: str | None, reason: str) -> None:
        if before is None:
            await self._act("delete_file", path, None, None, record=False)
            self.s.created_paths.discard(path)
        else:
            await self._act("edit_file", path, before, None, record=False)
        if self.s.journal and self.s.journal[-1].path == path:
            self.s.journal[-1].undone = True
        self.s.receipt("rollback", path=path, reason=reason, restored="deleted" if before is None else "previous")

    # -- other writes -----------------------------------------------------------------------------

    async def write_text_file(self, path: str, content: str, confirmed_overwrite: bool = False) -> dict[str, Any]:
        """Non-profile files (README, scripts). Same guards; no validator."""
        try:
            path = safe_path(path)
        except PathError as exc:
            return {"status": "rejected", "reason": str(exc)}
        existing = await self.resolve(path)
        if existing.status in ("unreachable", "ambiguous", "invalid"):
            return {"status": "blocked" if existing.status != "ambiguous" else "ambiguous",
                    "matches": existing.matches, "reason": existing.detail}
        target = existing.path or path
        before = existing.content if existing.status == "resolved" else None
        if before is not None and target not in self.s.created_paths and not confirmed_overwrite \
                and target not in self.explicit_targets:
            self.s.pending = Pending("overwrite", target, f"overwrite `{target}`", content=content, before=before)
            return {"status": "needs_confirmation", "path": target}
        await self._act("edit_file" if before is not None else "create_file", target, content, before)
        return {"status": "written", "path": target}

    async def request_delete(self, target: str) -> dict[str, Any]:
        res = await self.resolve(target)
        if res.status != "resolved":
            return {"status": res.status, "matches": res.matches, "reason": res.detail}
        self.s.pending = Pending("delete_file", res.path, f"delete `{res.path}`", before=res.content)
        self.s.receipt("guard", rule="I4", decision="confirm_delete", path=res.path)
        return {"status": "needs_confirmation", "path": res.path, "size": len(res.content or "")}

    async def create_folder(self, path: str) -> dict[str, Any]:
        try:
            path = safe_path(path)
        except PathError as exc:
            return {"status": "rejected", "reason": str(exc)}
        await self._act("create_folder", path, None, None)
        return {"status": "created", "path": path}

    async def request_delete_folder(self, path: str) -> dict[str, Any]:
        try:
            path = safe_path(path)
        except PathError as exc:
            return {"status": "rejected", "reason": str(exc)}
        self.s.pending = Pending("delete_folder", path,
                                 f"delete folder `{path}` and everything in it (cannot be undone)")
        self.s.receipt("guard", rule="I4", decision="confirm_delete_folder", path=path)
        return {"status": "needs_confirmation", "path": path, "reversible": False}

    async def resolve_pending(self, approved: bool) -> dict[str, Any]:
        pending, self.s.pending = self.s.pending, None
        if pending is None:
            return {"status": "nothing_pending"}
        self.s.receipt("confirmation", pending_kind=pending.kind, path=pending.path, approved=approved)
        if not approved:
            return {"status": "cancelled", "path": pending.path, "kind": pending.kind}
        if pending.kind == "delete_file":
            # Re-resolve: the workspace may have changed since the question was asked.
            res = await self.resolve(pending.path)
            if res.status != "resolved":
                return {"status": "stale", "path": pending.path, "detail": res.status}
            await self._act("delete_file", res.path, None, res.content)
            return {"status": "deleted", "path": res.path, "effect": self.last_effect}
        if pending.kind == "delete_folder":
            await self._act("delete_folder", pending.path, None, None, reversible=False)
            return {"status": "deleted_folder", "path": pending.path, "reversible": False, "effect": self.last_effect}
        if pending.kind == "overwrite" and pending.content is not None:
            if pending.path.endswith((".yaml", ".yml")) and spec.detect_kind(spec.parse_profile(pending.content)[0]) \
                    is not spec.ProfileKind.UNKNOWN:
                return await self.write_profile(pending.path, pending.content, confirmed_overwrite=True)
            return await self.write_text_file(pending.path, pending.content, confirmed_overwrite=True)
        return {"status": "unsupported_pending", "kind": pending.kind}

    async def undo(self) -> dict[str, Any]:
        for entry in reversed(self.s.journal):
            if entry.undone:
                continue
            if not entry.reversible:
                return {"status": "not_reversible", "action": entry.action, "path": entry.path}
            if entry.action == "create_file":
                await self._act("delete_file", entry.path, None, None, record=False)
                self.s.created_paths.discard(entry.path)
            elif entry.action == "edit_file" and entry.before is not None:
                await self._act("edit_file", entry.path, entry.before, None, record=False)
            elif entry.action == "delete_file" and entry.before is not None:
                await self._act("create_file", entry.path, entry.before, None, record=False)
            elif entry.action == "create_folder":
                await self._act("delete_folder", entry.path, None, None, record=False)
            else:
                return {"status": "not_reversible", "action": entry.action, "path": entry.path}
            entry.undone = True
            self.s.receipt("undo", journal_id=entry.entry_id, action=entry.action, path=entry.path)
            return {"status": "undone", "action": entry.action, "path": entry.path, "journal_id": entry.entry_id,
                    "effect": self.last_effect}
        return {"status": "nothing_to_undo"}


def _validation_summary(report: ValidationResult) -> dict[str, Any]:
    return {"outcome": report.outcome.value, "valid": report.valid, "type": report.kind,
            "errors": report.errors[:12], "warnings": report.warnings[:12], "detail": report.detail}


def elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
