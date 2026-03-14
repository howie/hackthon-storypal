"""WebSocket handler for StoryPal US5 — 適齡萬事通.

Handles ``ask`` and ``word_game`` message types, returning
``tutor_response`` messages.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from src.application.interfaces.llm_provider import ILLMProvider
from src.config import get_settings
from src.domain.services.story.tutor import TutorService
from src.infrastructure.websocket.base_handler import (
    BaseWebSocketHandler,
    MessageType,
    WebSocketMessage,
)

logger = logging.getLogger(__name__)


class TutorWebSocketHandler(BaseWebSocketHandler):
    """WebSocket handler for the 適齡萬事通 tutor feature."""

    def __init__(
        self,
        websocket: WebSocket,
        user_id: UUID,
        llm_provider: ILLMProvider,
        child_age: int = 4,
        logger_instance: logging.Logger | None = None,
    ) -> None:
        super().__init__(websocket, logger=logger_instance or logger)
        self._user_id = user_id
        self._tutor = TutorService(llm_provider)
        self._child_age = child_age
        self._history: list[dict[str, str]] = []
        self._message_count: int = 0
        self._max_messages: int = get_settings().max_chat_messages_per_session

    async def on_connect(self) -> None:
        await self.send_message(
            WebSocketMessage(
                type=MessageType.CONNECTED,
                data={"message": "小天老師來了！你想聊什麼呢？"},
            )
        )

    async def on_disconnect(self) -> None:
        self._logger.info(f"Tutor session disconnected for user {self._user_id}")

    async def run(self) -> None:
        """Main handler loop for tutor messages."""
        try:
            while self.is_connected:
                try:
                    data = await self._websocket.receive_json()
                except Exception:
                    break

                msg_type = data.get("type", "")
                msg_data = data.get("data", {})

                if msg_type == "ask":
                    await self._handle_ask(msg_data)
                elif msg_type == "word_game":
                    await self._handle_word_game(msg_data)
                elif msg_type == "ping":
                    await self.send_message(WebSocketMessage(type=MessageType.PONG))
                else:
                    self._logger.warning(f"Unknown tutor message type: {msg_type}")
        except Exception as e:
            self._logger.error(f"Tutor handler error: {e}")
            await self.send_error("TUTOR_ERROR", str(e))

    async def _check_message_limit(self) -> bool:
        """Increment counter and send error if limit exceeded. Returns True if blocked."""
        self._message_count += 1
        if self._message_count > self._max_messages:
            await self.send_error(
                "USAGE_LIMIT_EXCEEDED",
                f"本次對話已達上限 ({self._max_messages} 則)，請開啟新的對話。",
            )
            return True
        return False

    async def _handle_ask(self, data: dict[str, Any]) -> None:
        """Handle an ``ask`` message — child asks a question."""
        if await self._check_message_limit():
            return

        text = data.get("text", "").strip()
        if not text:
            await self.send_error("EMPTY_QUESTION", "請問一個問題喔！")
            return

        self._history.append({"role": "user", "content": text})

        try:
            answer = await self._tutor.answer_question(
                question=text,
                child_age=self._child_age,
                history=self._history,
            )
            self._history.append({"role": "assistant", "content": answer})

            await self._websocket.send_json(
                {
                    "type": "tutor_response",
                    "data": {
                        "text": answer,
                        "response_type": "answer",
                    },
                }
            )
        except Exception as e:
            self._logger.error(f"Tutor ask error: {e}")
            await self.send_error("TUTOR_ERROR", "老師現在有點忙，等一下再問好嗎？")

    async def _handle_word_game(self, data: dict[str, Any]) -> None:
        """Handle a ``word_game`` message — start or continue word chain."""
        if await self._check_message_limit():
            return

        action = data.get("action", "start")
        word = data.get("word", "")
        game_type = data.get("game_type", "word_chain")

        if action == "reply" and word:
            self._history.append({"role": "user", "content": f"我接「{word}」"})

        try:
            result = await self._tutor.play_word_game(
                word=word,
                game_type=game_type,
                child_age=self._child_age,
                history=self._history,
            )
            self._history.append({"role": "assistant", "content": result["text"]})

            await self._websocket.send_json(
                {
                    "type": "tutor_response",
                    "data": {
                        "text": result["text"],
                        "response_type": "word_game",
                        "game_type": game_type,
                        "current_word": result["current_word"],
                        "next_char": result["next_char"],
                    },
                }
            )
        except Exception as e:
            self._logger.error(f"Tutor word game error: {e}")
            await self.send_error("TUTOR_ERROR", "遊戲出了一點問題，我們重新開始好嗎？")
