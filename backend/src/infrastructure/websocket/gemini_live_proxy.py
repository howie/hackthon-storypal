"""Gemini Live API WebSocket proxy.

Feature: StoryPal — BE-C#1
Proxies browser WebSocket connections to Gemini Live API,
keeping the Google AI API key server-side only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import websockets
from fastapi import WebSocket

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

_GEMINI_LIVE_WS_URL = (
    "wss://generativelanguage.googleapis.com"
    "/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
)


class GeminiLiveProxyHandler:
    """Transparent WebSocket proxy between client and Gemini Live API.

    The browser connects to /story/tutor/live-ws (our backend).
    We forward all messages bidirectionally to/from the real Gemini endpoint,
    injecting the API key server-side so it never reaches the browser.
    """

    def __init__(self, client_ws: WebSocket) -> None:
        self._client_ws = client_ws

    async def handle(self) -> None:
        """Accept client connection, connect to Gemini, and proxy bidirectionally."""
        await self._client_ws.accept()

        from src.config import get_settings

        settings = get_settings()
        api_key = settings.gemini_api_key
        if not api_key:
            await self._client_ws.send_json(
                {"type": "error", "data": {"message": "API key not configured"}}
            )
            await self._client_ws.close(code=4500)
            return

        url = f"{_GEMINI_LIVE_WS_URL}?key={api_key}"
        logger.info("Opening Gemini Live proxy connection")
        try:
            async with websockets.connect(url, ping_interval=20) as gemini_ws:
                await asyncio.gather(
                    self._forward_client_to_gemini(gemini_ws),
                    self._forward_gemini_to_client(gemini_ws),
                    return_exceptions=True,
                )
        except Exception as exc:
            logger.warning("Gemini Live proxy error: %s", exc)
        finally:
            logger.info("Gemini Live proxy connection closed")

    async def _forward_client_to_gemini(self, gemini_ws: ClientConnection) -> None:
        """Forward messages from the browser client to Gemini."""
        try:
            while True:
                msg = await self._client_ws.receive()
                text = msg.get("text")
                data = msg.get("bytes")
                if text is not None:
                    await gemini_ws.send(text)
                elif data is not None:
                    await gemini_ws.send(data)
        except Exception:
            pass  # client disconnected

    async def _forward_gemini_to_client(self, gemini_ws: ClientConnection) -> None:
        """Forward messages from Gemini to the browser client."""
        try:
            async for message in gemini_ws:
                if isinstance(message, bytes):
                    await self._client_ws.send_bytes(message)
                else:
                    await self._client_ws.send_text(message)
        except Exception:
            pass  # gemini disconnected
