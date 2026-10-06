"""Test harness: Steward against the LOCAL_STUB IDE, with the stub playing the IDE frontend.

The real IDE executes each streamed action as it arrives. Here, `emit` parses every SSE event and applies
actions to the stub workspace immediately, which reproduces that ordering in-process.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from steward.agent import Steward
from steward.engine import SafeOps, SessionStore
from steward.ide import IdeClient
from steward.llm import LLM
from steward.retrieval import DocsIndex
from stub_ide.app import Workspace, create_app


@dataclass
class Turn:
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(e["response"] for e in self.events if "response" in e)

    @property
    def actions(self) -> list[dict[str, Any]]:
        return [e for e in self.events if "action" in e]


class Harness:
    def __init__(self, files: dict[str, str] | None = None, llm: LLM | None = None, backend_up: bool = True):
        self.ws = Workspace()
        for path, content in (files or {}).items():
            self.ws.files[path] = content
        self.stub = create_app(self.ws)
        transport = httpx.ASGITransport(app=self.stub) if backend_up else _DownTransport()
        self.ide = IdeClient("http://ide/api", transport=transport)
        self.sessions = SessionStore()
        self.steward = Steward(self.ide, DocsIndex(), llm)

    async def say(self, text: str, user_id: str = "u1") -> Turn:
        turn = Turn()
        session = self.sessions.get(user_id)

        async def emit(raw: str) -> None:
            assert raw.startswith("data: ") and raw.endswith("\n\n"), f"bad SSE framing: {raw!r}"
            event = json.loads(raw[len("data: "):-2])
            turn.events.append(event)
            if "action" in event:
                self.ws.apply(event)

        ops = SafeOps(self.ide, session, emit, validate_retries=2, validate_delay_s=0.01)
        await self.steward.handle(session, text, ops)
        return turn

    async def close(self) -> None:
        await self.ide.aclose()


class _DownTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused (simulated)", request=request)
