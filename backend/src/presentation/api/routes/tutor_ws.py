"""Tutor (適齡萬事通) WebSocket routes.

Separated from StoryPal WebSocket routes — Tutor is an independent feature
with its own ``/api/v1/tutor`` prefix.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Query, WebSocket

from src.infrastructure.auth.jwt import verify_access_token
from src.infrastructure.websocket.tutor_handler import TutorWebSocketHandler
from src.presentation.api.dependencies import get_llm_providers
from src.presentation.api.middleware.auth import APP_ENV, DEV_USER, DISABLE_AUTH

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def tutor_websocket(
    websocket: WebSocket,
    token: str = Query(default=""),
    child_age: int = Query(default=4, ge=1, le=8),
) -> None:
    """WebSocket endpoint for 適齡萬事通 tutor.

    Protocol:
    1. Client connects with auth token and child_age query param
    2. Client sends ``ask`` messages with ``{"text": "..."}``
    3. Client sends ``word_game`` messages with ``{"action": "start|reply", "word": "...", "game_type": "word_chain"}``
    4. Server responds with ``tutor_response`` messages
    """
    user_id: uuid.UUID | None = None

    if DISABLE_AUTH and APP_ENV != "production":
        user_id = uuid.UUID(DEV_USER.id)
    elif token:
        try:
            payload = verify_access_token(token)
            if payload:
                user_id = uuid.UUID(payload.sub)
        except Exception:
            pass

    if not user_id:
        await websocket.accept()
        await websocket.send_json({"type": "error", "data": {"message": "Unauthorized"}})
        await websocket.close(code=4001, reason="Unauthorized")
        return

    llm_providers = get_llm_providers()
    if not llm_providers:
        await websocket.accept()
        await websocket.send_json(
            {"type": "error", "data": {"message": "No LLM providers configured"}}
        )
        await websocket.close()
        return

    # Prefer gemini for tutor
    llm_provider = None
    for name in ("gemini", "openai", "anthropic", "azure-openai"):
        if name in llm_providers:
            llm_provider = llm_providers[name]
            break
    if not llm_provider:
        llm_provider = next(iter(llm_providers.values()))

    handler = TutorWebSocketHandler(
        websocket=websocket,
        user_id=user_id,
        llm_provider=llm_provider,
        child_age=child_age,
    )

    await handler.handle()


@router.websocket("/live-ws")
async def tutor_live_ws_proxy(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    """WebSocket proxy to Gemini Live API for 適齡萬事通.

    Keeps the Google AI API key server-side; client never sees the key.
    Auth: JWT token via ?token= query parameter (same as /ws endpoint).
    """
    user_id: uuid.UUID | None = None

    if DISABLE_AUTH and APP_ENV != "production":
        user_id = uuid.UUID(DEV_USER.id)
    elif token:
        try:
            payload = verify_access_token(token)
            if payload:
                user_id = uuid.UUID(payload.sub)
        except Exception:
            pass

    if not user_id:
        await websocket.accept()
        await websocket.send_json({"type": "error", "data": {"message": "Unauthorized"}})
        await websocket.close(code=4001, reason="Unauthorized")
        return

    from src.infrastructure.websocket.gemini_live_proxy import GeminiLiveProxyHandler

    handler = GeminiLiveProxyHandler(websocket)
    await handler.handle()
