"""Client for the HYPER-AI IDE backend agent endpoints, and the SSE event contract.

Contract source: https://ide-tutorial.hyperai.di.uoa.gr/hyperion-agent/ (read 2026-10-06).
  GET {base}/agent/file?path=<path|name>            200 {path, content} | 404 | 409 {matches}
  GET {base}/agent/validation/file?path=<path|name>  200 report | 404 | 409 {matches}
Every call returns an explicit outcome; network failures are values, never exceptions that could let
the agent proceed as if a check had passed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

import httpx

ACTIONS = {"create_folder", "delete_folder", "create_file", "edit_file", "delete_file"}


class Outcome(StrEnum):
    OK = "ok"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    UNREACHABLE = "unreachable"
    ERROR = "error"


@dataclass
class FileResult:
    outcome: Outcome
    path: str | None = None
    content: str | None = None
    matches: list[str] = field(default_factory=list)
    detail: str = ""
    latency_ms: int = 0


@dataclass
class ValidationResult:
    outcome: Outcome
    path: str | None = None
    kind: str | None = None
    valid: bool | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    matches: list[str] = field(default_factory=list)
    detail: str = ""
    latency_ms: int = 0


class PathError(ValueError):
    pass


def safe_path(path: str) -> str:
    """Workspace-relative POSIX path. Rejects absolute paths and parent traversal (contract rule)."""
    path = (path or "").strip().replace("\\", "/")
    if not path:
        raise PathError("empty path")
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        raise PathError(f"absolute paths are not allowed: {path!r}")
    parts = PurePosixPath(path).parts
    if any(p == ".." for p in parts):
        raise PathError(f"parent traversal is not allowed: {path!r}")
    return "/".join(p for p in parts if p not in ("", "."))


def is_bare_name(path: str) -> bool:
    return "/" not in path


def response_event(text: str) -> str:
    return f"data: {json.dumps({'response': text}, ensure_ascii=False)}\n\n"


def action_event(action: str, path: str, content: str | None = None) -> str:
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    payload: dict[str, Any] = {"action": action, "path": safe_path(path)}
    if action in ("create_file", "edit_file"):
        payload["content"] = content if content is not None else ""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class IdeClient:
    def __init__(self, base_url: str, timeout_s: float = 8.0, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, route: str, path: str) -> tuple[httpx.Response | None, str, int]:
        started = time.perf_counter()
        try:
            resp = await self._client.get(f"{self.base_url}{route}", params={"path": path})
            return resp, "", int((time.perf_counter() - started) * 1000)
        except httpx.HTTPError as exc:
            return None, f"{type(exc).__name__}: {exc}", int((time.perf_counter() - started) * 1000)

    async def read_file(self, path: str) -> FileResult:
        resp, err, ms = await self._get("/agent/file", path)
        if resp is None:
            return FileResult(Outcome.UNREACHABLE, detail=err, latency_ms=ms)
        body = _json(resp)
        if resp.status_code == 200:
            return FileResult(Outcome.OK, path=body.get("path", path), content=body.get("content", ""), latency_ms=ms)
        if resp.status_code == 404:
            return FileResult(Outcome.NOT_FOUND, detail=body.get("error", "File not found"), latency_ms=ms)
        if resp.status_code == 409:
            return FileResult(Outcome.AMBIGUOUS, matches=_matches(body), detail=body.get("error", ""), latency_ms=ms)
        return FileResult(Outcome.ERROR, detail=f"HTTP {resp.status_code}: {resp.text[:200]}", latency_ms=ms)

    async def validate_file(self, path: str) -> ValidationResult:
        resp, err, ms = await self._get("/agent/validation/file", path)
        if resp is None:
            return ValidationResult(Outcome.UNREACHABLE, detail=err, latency_ms=ms)
        body = _json(resp)
        if resp.status_code == 200:
            return ValidationResult(
                Outcome.OK, path=body.get("path", path), kind=body.get("type"), valid=bool(body.get("valid")),
                errors=list(body.get("errors") or []), warnings=list(body.get("warnings") or []), latency_ms=ms,
            )
        if resp.status_code == 404:
            return ValidationResult(Outcome.NOT_FOUND, detail=body.get("error", "File not found"), latency_ms=ms)
        if resp.status_code == 409:
            return ValidationResult(Outcome.AMBIGUOUS, matches=_matches(body), latency_ms=ms)
        return ValidationResult(Outcome.ERROR, detail=f"HTTP {resp.status_code}: {resp.text[:200]}", latency_ms=ms)


def _json(resp: httpx.Response) -> dict[str, Any]:
    try:
        value = resp.json()
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def _matches(body: dict[str, Any]) -> list[str]:
    out = []
    for m in body.get("matches") or []:
        out.append(m.get("path", str(m)) if isinstance(m, dict) else str(m))
    return out
