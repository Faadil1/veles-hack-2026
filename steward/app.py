"""HTTP surface of Hyperion Steward.

POST a JSON body {"user_id": "...", "text": "..."} and receive a text/event-stream of `data: {...}` events,
as specified by the Hyperion agent contract. Because the official starter's route name was not available
when this was written, the same handler is mounted on the routes a starter is likely to use; the route that
is actually called is recorded in receipts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import Steward
from .engine import SafeOps, SessionStore
from .ide import IdeClient, response_event
from .llm import LLM, AnthropicLLM, LLMError
from .retrieval import DocsIndex

log = logging.getLogger("steward")
CHAT_ROUTES = ("/", "/chat", "/api/chat", "/agent", "/hyperion", "/query", "/stream", "/v1/chat")


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20000)


def build_llm() -> LLM | None:
    if os.environ.get("STEWARD_DISABLE_LLM") == "1":
        return None
    try:
        return AnthropicLLM()
    except LLMError as exc:
        log.warning("language model disabled: %s", exc)
        return None


def create_app(ide_base_url: str | None = None, llm: LLM | None | str = "auto",
               ide_transport: Any = None) -> FastAPI:
    base = ide_base_url or os.environ.get("IDE_BACKEND_URL", "http://host.docker.internal:3001/api")
    state: dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        state["ide"] = IdeClient(base, transport=ide_transport)
        state["llm"] = build_llm() if llm == "auto" else llm
        state["steward"] = Steward(state["ide"], DocsIndex(), state["llm"])
        state["sessions"] = SessionStore()
        log.info("Hyperion Steward ready: ide=%s model=%s", base,
                 state["llm"].name if state["llm"] else "none (degraded mode)")
        yield
        await state["ide"].aclose()

    app = FastAPI(title="Hyperion Steward", version="0.1.0", lifespan=lifespan)
    app.state.steward_state = state

    async def chat(request: Request) -> StreamingResponse:
        try:
            payload = ChatRequest.model_validate(await request.json())
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"expected {{user_id, text}}: {exc}") from exc
        session = state["sessions"].get(payload.user_id)
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def emit(event: str) -> None:
            await queue.put(event)

        async def run() -> None:
            async with session.lock:
                session.receipt("route", path=request.url.path)
                ops = SafeOps(state["ide"], session, emit)
                try:
                    await state["steward"].handle(session, payload.text, ops)
                except Exception as exc:  # last line of defence: explain, never emit a half action
                    log.exception("turn failed")
                    session.receipt("turn_error", error=f"{type(exc).__name__}: {exc}"[:300])
                    await emit(response_event("Something went wrong on my side, and I stopped without changing "
                                              "anything further. Please try again."))
                finally:
                    await queue.put(None)

        task = asyncio.create_task(run())

        async def stream() -> AsyncIterator[str]:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
            await task

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    for route in CHAT_ROUTES:
        app.add_api_route(route, chat, methods=["POST"], include_in_schema=route == "/chat")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "ide_backend": base,
                "model": state["llm"].name if state.get("llm") else None,
                "degraded": state.get("llm") is None}

    @app.get("/receipts/{user_id}")
    async def receipts(user_id: str) -> JSONResponse:
        session = state["sessions"].peek(user_id)
        if session is None:
            return JSONResponse({"user_id": user_id, "receipts": [], "journal": []}, status_code=404)
        journal = [vars(e) | {"before": _clip(e.before), "after": _clip(e.after)} for e in session.journal]
        return JSONResponse({"user_id": user_id, "receipts": session.receipts, "journal": journal,
                             "pending": session.pending.summary if session.pending else None})

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return ("<!doctype html><title>Hyperion Steward</title><body style='font-family:system-ui;max-width:40rem;"
                "margin:3rem auto'><h1>Hyperion Steward</h1><p>HYPER-AI IDE agent. POST {user_id, text} to /chat "
                "for a Server-Sent Events stream. Receipts: <code>/receipts/&lt;user_id&gt;</code>.</p></body>")

    return app


def _clip(text: str | None, limit: int = 4000) -> str | None:
    if text is None:
        return None
    return text if len(text) <= limit else text[:limit] + f"... [{len(text) - limit} more chars]"


app = create_app()


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
