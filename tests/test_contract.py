"""HTTP-level contract: request shape, SSE framing, event keys."""

import json

import httpx
import pytest

from steward.app import create_app
from steward.llm import LLMTurn, ScriptedLLM
from stub_ide.app import create_app as create_stub



def _events(body: str) -> list[dict]:
    blocks = [b for b in body.split("\n\n") if b.strip()]
    assert all(b.startswith("data: ") for b in blocks), body
    return [json.loads(b[len("data: "):]) for b in blocks]


async def _client(llm):
    stub = create_stub()
    app = create_app(ide_base_url="http://ide/api", llm=llm, ide_transport=httpx.ASGITransport(app=stub))
    return app


@pytest.mark.parametrize("route", ["/chat", "/", "/api/chat"])
async def test_sse_stream_shape(route):
    app = await _client(ScriptedLLM([LLMTurn(text="Hello from Steward.")]))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
            r = await c.post(route, json={"user_id": "3f2a9c11", "text": "hi"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = _events(r.text)
    assert events and all(set(e) <= {"response", "action", "path", "content"} for e in events)
    assert "".join(e.get("response", "") for e in events) == "Hello from Steward."


async def test_bad_request_rejected():
    app = await _client(None)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
            r = await c.post("/chat", json={"text": "no user"})
    assert r.status_code == 422


async def test_receipts_endpoint_records_turn():
    app = await _client(None)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
            await c.post("/chat", json={"user_id": "u9", "text": "undo"})
            r = await c.get("/receipts/u9")
            h = await c.get("/health")
    kinds = [x["kind"] for x in r.json()["receipts"]]
    assert kinds[:2] == ["route", "user"] and "turn_done" in kinds
    assert h.json()["degraded"] is True


async def test_receipts_view_renders_and_escapes():
    app = await _client(None)
    async with app.router.lifespan_context(app), \
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        await c.post("/chat", json={"user_id": "v1", "text": "check <script>x</script>.yaml"})
        r = await c.get("/receipts/v1/view")
    assert r.status_code == 200 and "Steward receipts" in r.text
    assert "<script>x" not in r.text
