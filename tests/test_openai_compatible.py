"""OpenAI-compatible provider: wire translation and streamed tool calls, against a fake server."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from steward.llm import LLMError, OpenAICompatibleLLM
from tests.harness import Harness

DEVICE = (Path(__file__).parent / "fixtures" / "cookbook" / "device-hello-world-docker.yaml").read_text()


def fake_server(seen: list[dict]) -> FastAPI:
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        seen.append(body)
        if any(m["role"] == "tool" for m in body["messages"]):
            chunks = [{"choices": [{"delta": {"content": "Saved demo/hello.yaml"}}]},
                      {"choices": [{"delta": {"content": " and the validator accepts it."}, "finish_reason": "stop"}]},
                      {"choices": [], "usage": {"prompt_tokens": 120, "completion_tokens": 9}}]
        else:
            args = json.dumps({"path": "demo/hello.yaml", "yaml": DEVICE})
            half = len(args) // 2
            chunks = [
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "type": "function",
                                                         "function": {"name": "write_profile", "arguments": args[:half]}}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": args[half:]}}]},
                              "finish_reason": "tool_calls"}]},
                {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 40}},
            ]

        async def gen():
            for c in chunks:
                yield f"data: {json.dumps(c)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


async def test_streamed_tool_call_drives_a_real_steward_turn():
    seen: list[dict] = []
    llm = OpenAICompatibleLLM(base_url="http://fake/v1", model="test-model", api_key="",
                              transport=httpx.ASGITransport(app=fake_server(seen)))
    h = Harness({}, llm=llm)
    turn = await h.say("create a hello world device app")
    assert turn.actions[0] == {"action": "create_file", "path": "demo/hello.yaml", "content": DEVICE}
    assert "validator accepts it" in turn.text
    # second request carried the tool result back in OpenAI format
    assert seen[1]["messages"][-1]["role"] == "tool" and seen[1]["messages"][-1]["tool_call_id"] == "call_1"
    assert seen[1]["messages"][-2]["tool_calls"][0]["function"]["name"] == "write_profile"
    assert seen[0]["tools"][0]["type"] == "function"
    llm_receipts = [r for r in h.sessions.get("u1").receipts if r["kind"] == "llm"]
    assert llm_receipts[0]["input_tokens"] == 100 and llm_receipts[0]["output_tokens"] == 40


async def test_http_error_becomes_llm_error_and_degrades():
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def chat():
        return JSONResponse({"error": "model not found"}, status_code=404)

    llm = OpenAICompatibleLLM(base_url="http://fake/v1", model="m", api_key="", transport=httpx.ASGITransport(app=app))
    with pytest.raises(LLMError):
        await llm.step("s", [{"role": "user", "content": "hi"}], [], on_text=_noop)
    h = Harness({}, llm=llm)
    turn = await h.say("how do I deploy?")
    assert turn.actions == [] and "unavailable" in turn.text


async def _noop(_: str) -> None:
    return None


async def test_tool_call_printed_as_text_is_parsed_and_hidden():
    args = json.dumps({"path": "demo/t.yaml", "yaml": DEVICE})
    seen: list[dict] = []
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        seen.append(body)
        if any(m["role"] == "tool" for m in body["messages"]):
            chunks = [{"choices": [{"delta": {"content": "Done."}, "finish_reason": "stop"}]}]
        else:
            text = 'Creating it now. <tool_call>\n{"name": "write_profile", "arguments": ' + args + '}\n</tool_call>'
            chunks = [{"choices": [{"delta": {"content": text[:20]}}]}, {"choices": [{"delta": {"content": text[20:]}}]}]

        async def gen():
            for c in chunks:
                yield f"data: {json.dumps(c)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    llm = OpenAICompatibleLLM(base_url="http://fake/v1", model="m", api_key="", transport=httpx.ASGITransport(app=app))
    h = Harness({}, llm=llm)
    turn = await h.say("create the profile in demo/t.yaml")
    assert turn.actions and turn.actions[0]["path"] == "demo/t.yaml"
    assert "<tool_call>" not in turn.text and "Creating it now." in turn.text
