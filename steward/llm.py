"""Model access. One small interface, a real Anthropic implementation, and a scripted one for tests."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

OnText = Callable[[str], Awaitable[None]]


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    model: str = ""
    raw_content: list[dict[str, Any]] = field(default_factory=list)


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    name: str

    async def step(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                   on_text: OnText) -> LLMTurn: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None, api_key: str | None = None, max_tokens: int = 2048,
                 timeout_s: float = 60.0):
        import anthropic

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        self.model = model or os.environ.get("STEWARD_MODEL", "claude-sonnet-5-5")
        self.name = f"anthropic:{self.model}"
        self.max_tokens = max_tokens
        self._client = anthropic.AsyncAnthropic(api_key=key, timeout=timeout_s, max_retries=1)
        self._anthropic = anthropic

    async def step(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                   on_text: OnText) -> LLMTurn:
        started = time.perf_counter()
        text_parts: list[str] = []
        try:
            async with self._client.messages.stream(model=self.model, max_tokens=self.max_tokens, system=system,
                                                    messages=messages, tools=tools) as stream:
                async for event in stream:
                    if event.type == "text":
                        text_parts.append(event.text)
                        await on_text(event.text)
                final = await stream.get_final_message()
        except self._anthropic.APIError as exc:
            raise LLMError(f"{type(exc).__name__}: {getattr(exc, 'message', exc)}") from exc
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in final.content if b.type == "tool_use"]
        raw = [b.model_dump(exclude_none=True) for b in final.content]
        return LLMTurn(
            text="".join(text_parts), tool_calls=calls, stop_reason=final.stop_reason or "",
            input_tokens=final.usage.input_tokens, output_tokens=final.usage.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000), model=self.model, raw_content=raw,
        )


class ScriptedLLM:
    """Deterministic stand-in used by tests and the ablation harness. Plays back pre-written turns."""

    def __init__(self, turns: list[LLMTurn | Callable[[list[dict[str, Any]]], LLMTurn]]):
        self.turns = list(turns)
        self.name = "scripted"
        self.calls: list[list[dict[str, Any]]] = []

    async def step(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                   on_text: OnText) -> LLMTurn:
        self.calls.append(messages)
        if not self.turns:
            raise LLMError("scripted model has no more turns")
        turn = self.turns.pop(0)
        if callable(turn):
            turn = turn(messages)
        if turn.text:
            await on_text(turn.text)
        if not turn.raw_content:
            turn.raw_content = ([{"type": "text", "text": turn.text}] if turn.text else []) + [
                {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in turn.tool_calls]
        turn.stop_reason = "tool_use" if turn.tool_calls else "end_turn"
        turn.model = "scripted"
        return turn
