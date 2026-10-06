"""LOCAL_STUB of the HYPER-AI IDE, for tests and offline demos only.

Reproduces the documented agent contract (ide-tutorial.hyperai.di.uoa.gr/hyperion-agent/):
  - GET /api/agent/file            200 {path, content} | 404 | 409 {error, matches}
  - GET /api/agent/validation/file 200 {path, type, valid, errors, warnings} | 404 | 409
  - Name-only targets for delete_file / edit_file / delete_folder resolve to the FIRST match (documented hazard).
The validator here is Steward's own local spec checker. It is NOT the HYPER-AI validator; anything proven only
against this stub is LOCAL_STUB evidence.

Extra endpoints prefixed /__stub/ emulate the IDE frontend executing streamed actions, and let tests seed state.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from steward import spec


class Workspace:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.folders: set[str] = set()
        self.applied: list[dict[str, Any]] = []
        self.forced_invalid: dict[str, str] = {}  # path -> error message, to exercise validator rejection

    def matches(self, name_or_path: str) -> list[str]:
        if "/" in name_or_path:
            return [name_or_path] if name_or_path in self.files else []
        return [p for p in self.files if p.rsplit("/", 1)[-1] == name_or_path]

    def first_match(self, name_or_path: str) -> str | None:
        found = self.matches(name_or_path)
        return found[0] if found else None

    def apply(self, event: dict[str, Any]) -> dict[str, Any]:
        """Mimic the IDE frontend. Name-only targets use the first match, exactly as documented."""
        action, path = event.get("action"), event.get("path", "")
        outcome: dict[str, Any] = {"action": action, "requested": path}
        if action == "create_folder":
            self.folders.add(path)
        elif action == "delete_folder":
            target = path if ("/" in path or path in self.folders) else next(
                (f for f in self.folders if f.rsplit("/", 1)[-1] == path), path)
            self.folders = {f for f in self.folders if f != target and not f.startswith(target + "/")}
            self.files = {p: c for p, c in self.files.items() if not p.startswith(target + "/")}
            outcome["resolved"] = target
        elif action == "create_file":
            self.files[path] = event.get("content", "")
            if "/" in path:
                self.folders.add(path.rsplit("/", 1)[0])
        elif action == "edit_file":
            target = self.first_match(path) or path
            self.files[target] = event.get("content", "")
            outcome["resolved"] = target
        elif action == "delete_file":
            target = self.first_match(path)
            if target:
                del self.files[target]
            outcome["resolved"] = target
        self.applied.append(outcome)
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
        report = spec.check_profile(ws.files[body["path"]])
        errors = [{"line": 1, "column": 1, "field": i.field, "message": i.message} for i in report.errors]
        if body["path"] in ws.forced_invalid:
            errors.append({"line": 1, "column": 1, "field": "<stub>", "message": ws.forced_invalid[body["path"]]})
        if report.parse_error:
            errors.insert(0, {"line": 1, "column": 1, "field": "<yaml>", "message": report.parse_error})
        warnings = [{"line": 1, "column": 1, "field": i.field, "message": i.message}
                    for i in report.issues if i.severity is spec.Severity.WARNING]
        return JSONResponse({"path": body["path"], "type": report.kind.value, "valid": not errors,
                             "errors": errors, "warnings": warnings, "stub": True})

    class Seed(BaseModel):
        files: dict[str, str] = {}

    @app.post("/__stub/seed")
    def seed(payload: Seed) -> dict[str, Any]:
        ws.files.clear()
        ws.folders.clear()
        ws.applied.clear()
        for path, content in payload.files.items():
            ws.files[path] = content
            if "/" in path:
                ws.folders.add(path.rsplit("/", 1)[0])
        return {"files": list(ws.files)}

    @app.post("/__stub/apply")
    def apply(event: dict[str, Any]) -> dict[str, Any]:
        return ws.apply(event)

    @app.get("/__stub/tree")
    def tree() -> dict[str, Any]:
        return {"files": ws.files, "folders": sorted(ws.folders), "applied": ws.applied}

    return app


app = create_app()
