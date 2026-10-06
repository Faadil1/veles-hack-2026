"""LOCAL_STUB of the HYPER-AI IDE, for tests and offline demos only.

Mirrors the shipped IDE, read from the official images by CI recon (evidence/recon):
  backend donmichael/ide-backend:latest (server.js, validation/*.js)
  - GET /api/agent/file             direct path first; a bare name (no "/") is searched by file name:
                                    200 {path, content} | 404 | 409 {error, matches}
  - GET /api/agent/validation/file  same lookup, then the backend validator (here: steward.hyperai_schema, a port
                                    proven equal to the JavaScript validator by evaluation/validator_parity.py)
  - POST /api/file/create fails with 400 when the file exists; POST /api/folder/create fails when the folder exists.
  GUI donmichael/ide-gui:latest (assets/index-*.js)
  - Each streamed action is dispatched without waiting for the previous one; the agent is never told the outcome.
  - edit_file / delete_file / delete_folder resolve the target as: exact path, else the UNIQUE entry whose path ends
    with "/<name>". Zero or several matches: nothing happens, a WARN appears in the IDE status log only.
    (The published tutorial says "first match"; the shipped GUI does not do that.)
  - create_file on an existing path: the backend refuses, the GUI logs an ERROR, nothing changes.

Extra endpoints prefixed /__stub/ let tests seed state. `drop_actions=True` simulates a GUI that is not open,
so actions are never applied.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from steward import hyperai_schema


def _clean(path: str) -> str:
    return str(path or "").strip().strip("/")


class Workspace:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.folders: set[str] = set()
        self.applied: list[dict[str, Any]] = []
        self.status_log: list[str] = []  # what the IDE status bar would show; the agent never sees it
        self.forced_invalid: dict[str, str] = {}  # path -> error message, to exercise validator rejection
        self.drop_actions = False

    def seed(self, files: dict[str, str]) -> None:
        for path, content in files.items():
            self.files[path] = content
            self._add_parents(path)

    # backend lookupAgentFile
    def matches(self, name_or_path: str) -> list[str]:
        if name_or_path in self.files:
            return [name_or_path]
        if "/" in name_or_path:
            return []
        return sorted(p for p in self.files if p.rsplit("/", 1)[-1] == name_or_path)

    # GUI fa(): exact path, else unique suffix match
    def _gui_resolve(self, name: str, kind: str) -> tuple[str | None, list[str]]:
        pool = self.files.keys() if kind == "file" else self.folders
        if name in pool:
            return name, [name]
        found = sorted(p for p in pool if p.endswith("/" + name))
        return (found[0] if len(found) == 1 else None), found

    def _add_parents(self, path: str) -> None:
        parts = path.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            self.folders.add("/".join(parts[:i]))

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        """Execute one action the way the shipped GUI does."""
        action, path = event.get("action"), _clean(event.get("path", ""))
        outcome: dict[str, Any] = {"action": action, "requested": path, "applied": False}
        self.applied.append(outcome)
        if self.drop_actions:
            outcome["status"] = "dropped (GUI not open)"
            return outcome
        if not path:
            self.status_log.append(f"WARN Agent: {action} without a path - ignored.")
            return outcome
        if action == "create_folder":
            if path in self.folders:
                self.status_log.append("ERROR Agent action 'create_folder' failed: Folder already exists")
                return outcome
            self.folders.add(path)
            self._add_parents(path + "/x")
        elif action == "create_file":
            if path in self.files:
                self.status_log.append("ERROR Agent action 'create_file' failed: File already exists")
                return outcome
            self.files[path] = str(event.get("content") or "")
            self._add_parents(path)
        elif action in ("edit_file", "delete_file", "delete_folder"):
            kind = "folder" if action == "delete_folder" else "file"
            target, found = self._gui_resolve(path, kind)
            outcome["resolved"] = target
            if not target:
                why = "not found" if not found else f"matches {len(found)} {kind}s ({', '.join(found)})"
                self.status_log.append(f"WARN Agent: {kind} '{path}' {why} - nothing changed.")
                return outcome
            if action == "edit_file":
                self.files[target] = str(event.get("content") or "")
            elif action == "delete_file":
                del self.files[target]
            else:
                self.folders = {f for f in self.folders if f != target and not f.startswith(target + "/")}
                self.files = {p: c for p, c in self.files.items() if not p.startswith(target + "/")}
        else:
            self.status_log.append(f"WARN Agent sent unsupported action '{action}' - ignored.")
            return outcome
        outcome["applied"] = True
        return outcome


def create_app(workspace: Workspace | None = None) -> FastAPI:
    ws = workspace or Workspace()
    app = FastAPI(title="HYPER-AI IDE agent API (LOCAL_STUB)")
    app.state.workspace = ws

    def _lookup(path: str) -> tuple[int, dict[str, Any]]:
        found = ws.matches(path)
        if not found:
            return 404, {"error": "File not found"}
        if len(found) > 1:
            return 409, {"error": "Ambiguous file name", "matches": found}
        return 200, {"path": found[0]}

    @app.get("/api/agent/file")
    def read_file(path: str = Query(...)) -> JSONResponse:
        code, body = _lookup(path)
        if code == 200:
            body["content"] = ws.files[body["path"]]
        return JSONResponse(body, status_code=code)

    @app.get("/api/agent/validation/file")
    def validate_file(path: str = Query(...)) -> JSONResponse:
        code, body = _lookup(path)
        if code != 200:
            return JSONResponse(body, status_code=code)
        report = hyperai_schema.validate_profile(ws.files[body["path"]])
        errors = [{"line": 1, "column": 1, "field": e.path, "message": e.message} for e in report.errors]
        if body["path"] in ws.forced_invalid:
            errors.append({"line": 1, "column": 1, "field": "<stub>", "message": ws.forced_invalid[body["path"]]})
        warnings = [{"line": 1, "column": 1, "field": w.path, "message": w.message} for w in report.warnings]
        return JSONResponse({"path": body["path"], "type": report.type, "valid": not errors,
                             "errors": errors, "warnings": warnings, "stub": True})

    @app.get("/api/files")
    def list_files(path: str = "") -> JSONResponse:
        base = _clean(path)
        prefix = base + "/" if base else ""
        names: dict[str, str] = {}
        for p in ws.files:
            if p.startswith(prefix):
                head = p[len(prefix):].split("/", 1)
                names.setdefault(head[0], "file" if len(head) == 1 else "folder")
        for f in ws.folders:
            if f.startswith(prefix) and f != base:
                names.setdefault(f[len(prefix):].split("/", 1)[0], "folder")
        return JSONResponse([{"name": n, "type": t, "path": prefix + n} for n, t in sorted(names.items())])

    class Seed(BaseModel):
        files: dict[str, str] = {}

    @app.post("/__stub/seed")
    def seed(payload: Seed) -> dict[str, Any]:
        ws.files.clear()
        ws.folders.clear()
        ws.applied.clear()
        for path, content in payload.files.items():
            ws.files[path] = content
            ws._add_parents(path)
        return {"files": list(ws.files)}

    @app.post("/__stub/apply")
    def apply(event: dict[str, Any]) -> dict[str, Any]:
        return ws.apply(event)

    @app.get("/__stub/tree")
    def tree() -> dict[str, Any]:
        return {"files": ws.files, "folders": sorted(ws.folders), "applied": ws.applied}

    return app


app = create_app()
