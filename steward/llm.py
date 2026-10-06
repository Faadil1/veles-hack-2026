"""Model access. One small interface, a real Anthropic implementation, and a scripted one for tests."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from collections.abc import Awaitable, Callable

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


class OpenAICompatibleLLM:
    """Any OpenAI-compatible /chat/completions endpoint: an organiser-provided model, a local server (Ollama,
    vLLM, llama.cpp) or a hosted provider. Uses httpx only. Translates the Anthropic-style messages the agent
    loop keeps (text / tool_use / tool_result blocks) to and from the OpenAI wire format."""

    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None,
                 max_tokens: int = 2048, timeout_s: float | None = None, transport: Any = None):
        import httpx

        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
        if not self.base_url:
            raise LLMError("OPENAI_BASE_URL is not set")
        self.model = model or os.environ.get("STEWARD_MODEL") or ""
        if not self.model:
            raise LLMError("STEWARD_MODEL is not set for the OpenAI-compatible provider")
        key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        self.name = f"openai-compatible:{self.model}@{self.base_url}"
        self.max_tokens = max_tokens
        timeout_s = timeout_s if timeout_s is not None else float(os.environ.get("STEWARD_LLM_TIMEOUT", "90"))
        self._client = httpx.AsyncClient(timeout=timeout_s, headers=headers, transport=transport)
        self._httpx = httpx

    @staticmethod
    def to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for msg in messages:
            content = msg["content"]
            if isinstance(content, str):
                out.append({"role": msg["role"], "content": content})
                continue
            if msg["role"] == "assistant":
                text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
                calls = [{"id": b["id"], "type": "function",
                          "function": {"name": b["name"], "arguments": json.dumps(b.get("input", {}))}}
                         for b in content if b.get("type") == "tool_use"]
                item: dict[str, Any] = {"role": "assistant", "content": text or None}
                if calls:
                    item["tool_calls"] = calls
                out.append(item)
            else:
                for b in content:
                    if b.get("type") == "tool_result":
                        out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b.get("content", "")})
                    elif b.get("type") == "text":
                        out.append({"role": "user", "content": b.get("text", "")})
        return out

    @staticmethod
    def to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                                  "parameters": t.get("input_schema", {"type": "object"})}}
                for t in tools]

    async def step(self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                   on_text: OnText) -> LLMTurn:
        started = time.perf_counter()
        body = {"model": self.model, "max_tokens": self.max_tokens, "stream": True,
                "stream_options": {"include_usage": True},
                "messages": self.to_openai_messages(system, messages), "tools": self.to_openai_tools(tools)}
        text_parts: list[str] = []
        calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, Any] = {}
        finish = ""
        try:
            async with self._client.stream("POST", f"{self.base_url}/chat/completions", json=body) as resp:
                if resp.status_code >= 400:
                    detail = (await resp.aread()).decode(errors="replace")[:300]
                    raise LLMError(f"HTTP {resp.status_code}: {detail}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    usage = chunk.get("usage") or usage
                    for choice in chunk.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            text_parts.append(delta["content"])
                            # Some local models print tool calls as text (<tool_call>{...}</tool_call>).
                            # Stop streaming once that marker appears; it is parsed into a real call below.
                            shown = "".join(text_parts[:-1])
                            if "<tool_call>" not in shown:
                                visible = delta["content"]
                                joined = shown + visible
                                if "<tool_call>" in joined:
                                    visible = joined[: joined.index("<tool_call>")][len(shown):]
                                if visible:
                                    await on_text(visible)
                        for tc in delta.get("tool_calls") or []:
                            slot = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "args": ""})
                            slot["id"] = tc.get("id") or slot["id"]
                            fn = tc.get("function") or {}
                            slot["name"] = fn.get("name") or slot["name"]
                            slot["args"] += fn.get("arguments") or ""
                        finish = choice.get("finish_reason") or finish
        except self._httpx.HTTPError as exc:
            raise LLMError(f"{type(exc).__name__}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"malformed stream chunk: {exc}") from exc
        tool_calls = []
        for idx in sorted(calls):
            slot = calls[idx]
            try:
                args = json.loads(slot["args"] or "{}")
            except json.JSONDecodeError:
                args = {"_unparsed_arguments": slot["args"][:500]}
            tool_calls.append(ToolCall(slot["id"] or f"call_{idx}", slot["name"], args))
        text = "".join(text_parts)
        if not tool_calls and "<tool_call>" in text:
            text, tool_calls = _extract_text_tool_calls(text)
        raw = ([{"type": "text", "text": text}] if text else []) + [
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in tool_calls]
        return LLMTurn(text=text, tool_calls=tool_calls, stop_reason=finish or "stop",
                       input_tokens=int(usage.get("prompt_tokens") or 0),
                       output_tokens=int(usage.get("completion_tokens") or 0),
                       latency_ms=int((time.perf_counter() - started) * 1000), model=self.model, raw_content=raw)


def _extract_text_tool_calls(text: str) -> tuple[str, list[ToolCall]]:
    """Parse <tool_call>{"name": ..., "arguments": {...}}</tool_call> blocks a model printed as text."""
    import re

    calls: list[ToolCall] = []
    for i, block in enumerate(re.findall(r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)", text, re.S)):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        args = data.get("arguments", data.get("parameters", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if data.get("name"):
            calls.append(ToolCall(f"text_call_{i}", str(data["name"]), dict(args)))
    visible = text[: text.index("<tool_call>")].rstrip()
    return visible, calls


HYPERAI_BASE_URL = "https://legion1.di.uoa.gr/v1"  # organiser LLM server (hyperion-starter main.py)
HYPERAI_MODEL = "llama3.1"                          # model named in hyperion-starter main.py


def build_llm_from_env() -> LLM | None:
    """Default: the organiser-provided OpenAI-compatible server, exactly as the official starter configures it
    (BASE_URL legion1, model llama3.1, key in API_KEY). Overrides:
      STEWARD_PROVIDER = openai_compatible (default) | anthropic | none
      OPENAI_BASE_URL / STEWARD_MODEL / API_KEY (or OPENAI_API_KEY) for any OpenAI-compatible server (e.g. Ollama)
    """
    provider = os.environ.get("STEWARD_PROVIDER", "openai_compatible").lower()
    if provider == "none" or os.environ.get("STEWARD_DISABLE_LLM") == "1":
        return None
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("STEWARD_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
        return AnthropicLLM()
    key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    return OpenAICompatibleLLM(base_url=os.environ.get("OPENAI_BASE_URL") or HYPERAI_BASE_URL,
                               model=os.environ.get("STEWARD_MODEL") or HYPERAI_MODEL, api_key=key)


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
