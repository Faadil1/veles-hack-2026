"""Live vertical slice against the real HYPER-AI IDE backend (donmichael/ide-backend:latest).

Steward runs with its real IdeClient pointed at the running backend. The model is scripted (tool calls fixed) so the
run is deterministic and needs no key. Streamed actions are executed by GuiReplica, a line-for-line port of the
shipped GUI's action handlers (donmichael/ide-gui:latest, assets/index-*.js): same backend endpoints, same
exact-or-unique-suffix name resolution, dispatched fire-and-forget exactly like the GUI.

Evidence class: LIVE backend + real validator; GUI behaviour replicated (PARTIAL for the GUI itself).
Run: python -m evaluation.live_slice --backend http://localhost:3001/api [--out evidence/live-slice/live.json]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

from steward.agent import Steward
from steward.engine import SafeOps, SessionStore
from steward.ide import IdeClient
from steward.llm import LLMTurn, ScriptedLLM, ToolCall
from steward.retrieval import DocsIndex

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "cookbook"
DEVICE = (FIX / "device-hello-world-docker.yaml").read_text()
NATIVE = (FIX / "native-hello-world.yaml").read_text()
PREFIX = "steward-live"


class GuiReplica:
    """Port of the GUI's q2 action table. Each action runs as its own task, like `r(V)` without await."""

    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.http = httpx.AsyncClient(timeout=10)
        self.tasks: list[asyncio.Task] = []
        self.log: list[str] = []

    async def _list_all(self, path: str = "") -> list[dict[str, Any]]:
        out = []
        for e in (await self.http.get(f"{self.base}/files", params={"path": path})).json():
            out.append(e)
            if e.get("type") == "folder":
                out.extend(await self._list_all(e["path"]))
        return out

    async def _resolve(self, name: str, kind: str) -> tuple[str | None, list[str]]:
        paths = [e["path"] for e in await self._list_all() if e.get("type") == kind]
        if name in paths:
            return name, [name]
        found = [p for p in paths if p.endswith("/" + name)]
        return (found[0] if len(found) == 1 else None), found

    async def _run(self, ev: dict[str, Any]) -> None:
        action, path = ev.get("action"), str(ev.get("path") or "").strip().strip("/")
        try:
            if action == "create_folder":
                r = await self.http.post(f"{self.base}/folder/create", json={"path": path})
            elif action == "create_file":
                r = await self.http.post(f"{self.base}/file/create", json={"path": path, "content": ev.get("content", "")})
            elif action in ("edit_file", "delete_file", "delete_folder"):
                target, found = await self._resolve(path, "folder" if action == "delete_folder" else "file")
                if not target:
                    self.log.append(f"WARN {action} '{path}': {len(found)} matches - nothing changed")
                    return
                if action == "edit_file":
                    r = await self.http.post(f"{self.base}/file", json={"path": target, "content": ev.get("content", "")})
                else:
                    r = await self.http.delete(f"{self.base}/delete", params={"path": target})
            else:
                self.log.append(f"WARN unsupported action {action}")
                return
            self.log.append(f"{'OK' if r.status_code == 200 else 'ERROR'} {action} {path} [{r.status_code}]")
        except httpx.HTTPError as exc:
            self.log.append(f"ERROR {action} {path}: {exc}")

    def dispatch(self, ev: dict[str, Any]) -> None:
        self.tasks.append(asyncio.create_task(self._run(ev)))

    async def settle(self) -> None:
        if self.tasks:
            await asyncio.gather(*self.tasks)
        self.tasks.clear()


def call(name: str, /, **args: Any) -> LLMTurn:
    return LLMTurn(text="", tool_calls=[ToolCall(f"c-{name}-{time.time_ns()}", name, args)])


STEPS: list[dict[str, Any]] = [
    {"id": "L1", "title": "Create a device profile from parameters (builder, real validator)",
     "say": "create a device app for nginx", "model": [call("create_profile", path=f"{PREFIX}/web.yaml", kind="device",
                                                           name="web", image="nginx:1.27", ports=[80])],
     "expect": lambda r, t: r.get("status") == "written_valid" and r.get("effect") == "verified"},
    {"id": "L2", "title": "Write the official native cookbook example: schema-valid, runnability blocker surfaced",
     "say": "save the native hello world example", "model": [call("write_profile", path=f"{PREFIX}/native.yaml",
                                                                  yaml=NATIVE)],
     "expect": lambda r, t: r.get("status") == "written_valid"
     and r.get("runnability", {}).get("verdict") == "will_not_run"},
    {"id": "L3", "title": "Seed a second app.yaml, then delete by the shared bare name: Steward asks, nothing sent",
     "setup": [("create", f"{PREFIX}/edge/app.yaml", DEVICE), ("create", f"{PREFIX}/cloud/app.yaml", DEVICE)],
     "say": "delete app.yaml", "model": [call("delete_file", path="app.yaml")],
     "expect": lambda r, t: r.get("status") == "ambiguous" and len(r.get("matches", [])) >= 2},
    {"id": "L4", "title": "A spec-invalid profile is stopped before it reaches the workspace",
     "say": "write this", "model": [call("write_profile", path=f"{PREFIX}/bad.yaml",
                                         yaml=DEVICE.replace("kind: DockerImage", "kind: Kubernetes"))],
     "expect": lambda r, t: r.get("status") == "local_check_failed"},
    {"id": "L5", "title": "Delete with confirmation, verified by read-back",
     "say": f"delete {PREFIX}/web.yaml", "model": [call("delete_file", path=f"{PREFIX}/web.yaml")],
     "then": "yes", "expect": lambda r, t: "Deleted" in t},
    {"id": "L6", "title": "Undo restores the deleted file byte for byte",
     "say": "undo", "expect": lambda r, t: "Undone" in t},
]


async def run(backend: str) -> dict[str, Any]:
    ide = IdeClient(backend)
    gui = GuiReplica(backend)
    sessions = SessionStore()
    results = []
    original: str | None = None
    # clean slate for our prefix
    await gui.http.delete(f"{gui.base}/delete", params={"path": PREFIX})
    for step in STEPS:
        for _kind, path, content in step.get("setup", []):
            await gui.http.post(f"{gui.base}/file/create", json={"path": path, "content": content})
        llm = ScriptedLLM(list(step.get("model", [])) + [LLMTurn(text="ok")])
        steward = Steward(ide, DocsIndex(), llm)
        session = sessions.get("live-user")
        events: list[dict[str, Any]] = []

        async def emit(raw: str, events: list[dict[str, Any]] = events) -> None:
            ev = json.loads(raw[len("data: "):-2])
            events.append(ev)
            if "action" in ev:
                gui.dispatch(ev)

        ops = SafeOps(ide, session, emit)
        started = time.perf_counter()
        await steward.handle(session, step["say"], ops)
        if step.get("then"):
            await steward.handle(session, step["then"], ops)
        await gui.settle()
        if step["id"] == "L1":
            original = (await ide.read_file(f"{PREFIX}/web.yaml")).content
        tool_results = [r for r in session.receipts if r["kind"] == "tool_result"]
        last = tool_results[-1].get("result", {}) if tool_results else {}
        text = "".join(e.get("response", "") for e in events)
        if not last:
            last = _last_result(llm)
        ok = bool(step["expect"](last, text))
        results.append({"id": step["id"], "title": step["title"], "passed": ok,
                        "seconds": round(time.perf_counter() - started, 2),
                        "actions": [f"{e['action']} {e['path']}" for e in events if "action" in e],
                        "steward_said": text[:600], "result": {k: last.get(k) for k in
                                                               ("status", "effect", "matches", "validator")}})
    restored = await ide.read_file(f"{PREFIX}/web.yaml")
    identical = restored.content == original
    receipts = sessions.get("live-user").receipts
    effects = [r for r in receipts if r["kind"] == "effect"]
    report: dict[str, Any] = {
        "evidence_class": "LIVE ide-backend + real validator; GUI action handlers replicated",
        "backend": backend, "passed": sum(r["passed"] for r in results), "total": len(results),
        "undo_restored_file": restored.outcome.value, "undo_restored_identical_bytes": identical,
        "effects": {s: sum(e["status"] == s for e in effects) for s in ("verified", "not_seen", "unobservable")},
        "validator_calls": [{k: r.get(k) for k in ("path", "outcome", "valid", "attempts")} for r in receipts
                            if r["kind"] == "validate_file"],
        "gui_log": gui.log, "results": results,
    }
    await gui.http.delete(f"{gui.base}/delete", params={"path": PREFIX})
    await gui.http.aclose()
    await ide.aclose()
    return report


def _last_result(llm: ScriptedLLM) -> dict[str, Any]:
    for messages in reversed(llm.calls):
        for m in reversed(messages):
            if isinstance(m.get("content"), list):
                for b in reversed(m["content"]):
                    if b.get("type") == "tool_result":
                        try:
                            return json.loads(b["content"])
                        except (TypeError, ValueError):
                            return {}
    return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="http://localhost:3001/api")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    report = asyncio.run(run(args.backend))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
    print(text[:4000])
    raise SystemExit(0 if report["passed"] == report["total"] and report["undo_restored_identical_bytes"] else 1)


if __name__ == "__main__":
    main()
