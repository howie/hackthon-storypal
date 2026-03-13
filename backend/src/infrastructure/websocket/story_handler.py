"""WebSocket handler for StoryPal interactive story sessions.

Feature: StoryPal — AI Interactive Story Companion

Handles the story interaction protocol: configure → segments → choices → continuation.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from src.application.interfaces.llm_provider import ILLMProvider
from src.application.interfaces.tts_provider import ITTSProvider
from src.domain.entities.audio import AudioFormat
from src.domain.entities.story import (
    SceneInfo,
    StoryCharacter,
    StorySession,
    StorySessionStatus,
    StoryTemplate,
    StoryTurnType,
)
from src.domain.entities.tts import TTSRequest
from src.domain.repositories.story_repository import IStoryRepository
from src.domain.services.story.engine import StoryEngine, StorySegment
from src.infrastructure.websocket.base_handler import (
    BaseWebSocketHandler,
    MessageType,
    WebSocketMessage,
)

logger = logging.getLogger(__name__)


class StoryMessageType:
    """Story-specific message types."""

    # Client -> Server
    STORY_CONFIGURE = "story_configure"
    STORY_CHOICE = "story_choice"

    # Server -> Client
    STORY_SEGMENT = "story_segment"
    CHOICE_PROMPT = "choice_prompt"
    SCENE_CHANGE = "scene_change"
    STORY_END = "story_end"


class StoryWebSocketHandler(BaseWebSocketHandler):
    """Handles WebSocket communication for interactive story sessions."""

    def __init__(
        self,
        websocket: WebSocket,
        user_id: UUID,
        llm_provider: ILLMProvider,
        repo_factory: Callable[[], IStoryRepository],
        tts_provider: ITTSProvider | None = None,
        logger_instance: logging.Logger | None = None,
    ) -> None:
        super().__init__(websocket, logger=logger_instance or logger)
        self._user_id = user_id
        self._engine = StoryEngine(llm_provider)
        self._tts = tts_provider
        self._repo_factory = repo_factory
        self._narration_voice = "Kore"
        self._session: StorySession | None = None
        self._turn_counter = 0
        self._is_generating = False
        self._db_session_id: UUID | None = None

    async def on_connect(self) -> None:
        """Handle new connection."""
        await self.send_message(
            WebSocketMessage(
                type=MessageType.CONNECTED,
                data={"message": "歡迎來到 StoryPal！準備好聽故事了嗎？"},
            )
        )

    async def on_disconnect(self) -> None:
        """Handle disconnect - save session state."""
        if self._session and self._session.status == StorySessionStatus.ACTIVE:
            self._session.pause()
        if self._db_session_id:
            await self._update_db_session_status("paused")
        self._logger.info(f"Story session disconnected for user {self._user_id}")

    async def run(self) -> None:
        """Main handler loop for story messages."""
        try:
            while self.is_connected:
                try:
                    data = await self._websocket.receive_json()
                except Exception:
                    break

                msg_type = data.get("type", "")
                msg_data = data.get("data", {})

                if msg_type == StoryMessageType.STORY_CONFIGURE:
                    await self._handle_configure(msg_data)
                elif msg_type == StoryMessageType.STORY_CHOICE:
                    await self._handle_choice(msg_data)
                elif msg_type == "text_input":
                    await self._handle_text_input(msg_data)
                elif msg_type == "interrupt":
                    await self._handle_interrupt()
                elif msg_type == "ping":
                    await self.send_message(WebSocketMessage(type=MessageType.PONG))
                else:
                    self._logger.warning(f"Unknown message type: {msg_type}")
        except (WebSocketDisconnect, RuntimeError) as e:
            self._mark_disconnected("run", e)
        except Exception as e:
            self._logger.error(f"Story handler error: {e}")
            await self.send_error("STORY_ERROR", str(e))

    async def _handle_configure(self, data: dict[str, Any]) -> None:
        """Handle story configuration and start the story."""
        template_id = data.get("template_id")
        language = data.get("language", "zh-TW")
        characters_config = data.get("characters_config")
        self._logger.info(
            "[StoryWS] configure received: template_id=%s language=%s", template_id, language
        )

        # Find template from DB
        template = None
        if template_id:
            template = await self._load_template_from_db(template_id)

        if not template:
            self._logger.warning("[StoryWS] template not found: %s", template_id)
            await self.send_error("TEMPLATE_NOT_FOUND", f"Template {template_id} not found")
            return

        self._logger.info("[StoryWS] template found: %s (%s)", template.name, template.id)

        # Create in-memory session
        from src.domain.entities.story import StoryCharacter

        chars = template.characters
        if characters_config:
            chars = [StoryCharacter(**c) for c in characters_config]

        system_prompt = self._engine._build_system_prompt(template)
        self._logger.debug("[StoryWS][configure] system_prompt=\n%s", system_prompt)

        self._session = StorySession(
            title=template.name,
            language=language,
            user_id=str(self._user_id),
            template_id=template.id,
            characters_config=chars,
            story_state={"system_prompt": system_prompt},
        )
        self._turn_counter = 0

        # Persist session to DB (fire-and-await to get DB session ID)
        self._logger.info("[StoryWS] creating DB session...")
        self._db_session_id = await self._create_db_session(
            session_id=self._session.id,
            template_id=template.id,
            title=template.name,
            language=language,
            system_prompt=system_prompt,
            chars=chars,
        )
        self._logger.info("[StoryWS] DB session created: %s", self._db_session_id)

        # Generate opening
        self._is_generating = True
        try:
            self._logger.info("[StoryWS] calling LLM to generate opening...")
            segments, scene_change, is_complete = await self._engine.start_story(template, language)
            self._logger.info(
                "[StoryWS] LLM returned %d segments, scene_change=%s, is_complete=%s",
                len(segments),
                scene_change is not None,
                is_complete,
            )
            await self._send_story_segments(segments, scene_change, is_complete)
            self._logger.info("[StoryWS] segments sent to client")
        except TimeoutError:
            self._logger.error("[StoryWS] story generation timed out")
            await self.send_error("TIMEOUT", "故事生成超時，請重試")
        except (WebSocketDisconnect, RuntimeError) as e:
            self._mark_disconnected("generation", e)
        except Exception as e:
            self._logger.exception("[StoryWS] failed to start story: %s", e)
            await self.send_error("GENERATION_ERROR", f"無法開始故事：{e}")
        finally:
            self._is_generating = False

    async def _handle_choice(self, data: dict[str, Any]) -> None:
        """Handle child's choice selection."""
        if not self._session:
            await self.send_error("NO_SESSION", "尚未開始故事")
            return

        choice = data.get("choice", "")
        if not choice:
            await self.send_error("EMPTY_CHOICE", "請選擇一個選項")
            return

        # Record child's choice as a turn
        from src.domain.entities.story import StoryTurn

        self._turn_counter += 1
        child_turn = StoryTurn(
            session_id=self._session.id,
            turn_number=self._turn_counter,
            turn_type=StoryTurnType.CHILD_RESPONSE,
            content=choice,
            child_choice=choice,
        )
        self._session.add_turn(child_turn)
        asyncio.create_task(
            self._save_turn_to_db(child_turn.turn_number, child_turn.turn_type.value, choice)
        )

        # Continue story
        self._is_generating = True
        try:
            segments, scene_change, is_complete = await self._engine.continue_story(
                self._session, choice
            )
            await self._send_story_segments(segments, scene_change, is_complete)
        except TimeoutError:
            self._logger.error("[StoryWS] story continuation timed out")
            await self.send_error("TIMEOUT", "故事生成超時，請重試")
        except (WebSocketDisconnect, RuntimeError) as e:
            self._mark_disconnected("continuation", e)
        except Exception as e:
            self._logger.exception("[StoryWS] failed to continue story: %s", e)
            await self.send_error("GENERATION_ERROR", f"無法繼續故事：{e}")
        finally:
            self._is_generating = False

    async def _handle_text_input(self, data: dict[str, Any]) -> None:
        """Handle free text input (questions or responses)."""
        if not self._session:
            await self.send_error("NO_SESSION", "尚未開始故事")
            return

        text = data.get("text", "")
        if not text:
            return

        # Determine if this is a question or a story response
        is_question = any(
            text.strip().endswith(c) for c in ("？", "?", "嗎", "呢", "為什麼", "怎麼")
        )

        from src.domain.entities.story import StoryTurn

        self._turn_counter += 1
        child_turn = StoryTurn(
            session_id=self._session.id,
            turn_number=self._turn_counter,
            turn_type=StoryTurnType.QUESTION if is_question else StoryTurnType.CHILD_RESPONSE,
            content=text,
        )
        self._session.add_turn(child_turn)
        asyncio.create_task(
            self._save_turn_to_db(child_turn.turn_number, child_turn.turn_type.value, text)
        )

        self._is_generating = True
        try:
            if is_question:
                segments, scene_change, is_complete = await self._engine.handle_question(
                    self._session, text
                )
            else:
                segments, scene_change, is_complete = await self._engine.continue_story(
                    self._session, text
                )
            await self._send_story_segments(segments, scene_change, is_complete)
        except TimeoutError:
            self._logger.error("[StoryWS] text input handling timed out")
            await self.send_error("TIMEOUT", "處理超時，請重試")
        except (WebSocketDisconnect, RuntimeError) as e:
            self._mark_disconnected("text_input", e)
        except Exception as e:
            self._logger.exception("[StoryWS] failed to handle input: %s", e)
            await self.send_error("GENERATION_ERROR", f"處理失敗：{e}")
        finally:
            self._is_generating = False

    async def _handle_interrupt(self) -> None:
        """Handle interrupt/barge-in."""
        self._is_generating = False
        if self._session:
            self._session.pause()
        await self.send_message(
            WebSocketMessage(
                type=MessageType.INTERRUPTED,
                data={"message": "故事已暫停"},
            )
        )

    async def _synthesize_segment(
        self,
        segment: StorySegment,
        characters: list[StoryCharacter],
    ) -> str | None:
        """Return base64-encoded MP3 or None if TTS unavailable."""
        if not self._tts:
            self._logger.info("[StoryWS] TTS not available, skipping synthesis")
            return None
        voice_id = self._narration_voice
        if segment.character_name:
            for c in characters:
                if c.name == segment.character_name:
                    voice_id = c.voice_id or self._narration_voice
                    break
        try:
            req = TTSRequest(
                text=segment.content,
                voice_id=voice_id,
                provider="gemini-pro",
                language="zh-TW",
                output_format=AudioFormat.MP3,
            )
            result = await self._tts.synthesize(req)
            audio_b64 = base64.b64encode(result.audio.data).decode()
            self._logger.info(
                "[StoryWS] TTS synthesized %d bytes for: %.30s...",
                len(result.audio.data),
                segment.content,
            )
            return audio_b64
        except Exception as e:
            self._logger.warning("[StoryWS] TTS synthesis failed: %s", e, exc_info=True)
            return None

    async def _send_story_segments(
        self,
        segments: list[StorySegment],
        scene_change: SceneInfo | None,
        is_complete: bool = False,
    ) -> None:
        """Send story segments to client with appropriate delays."""
        if not self.is_connected:
            return

        # Send scene change first if present
        if scene_change:
            sent = await self._safe_send_json(
                {
                    "type": StoryMessageType.SCENE_CHANGE,
                    "data": {
                        "scene_name": scene_change.name,
                        "description": scene_change.description,
                        "bgm_prompt": scene_change.bgm_prompt,
                        "mood": scene_change.mood,
                    },
                }
            )
            if not sent:
                return
            if self._session:
                self._session.current_scene = scene_change.name

        chars = self._session.characters_config if self._session else []

        # Send each segment with a small delay for natural pacing
        for seg in segments:
            if not self.is_connected or not self._is_generating:
                break

            # Record turn
            from src.domain.entities.story import StoryTurn

            self._turn_counter += 1
            turn = StoryTurn(
                session_id=self._session.id if self._session else UUID(int=0),
                turn_number=self._turn_counter,
                turn_type=seg.type,
                content=seg.content,
                character_name=seg.character_name,
                bgm_scene=seg.scene,
            )
            if self._session:
                self._session.add_turn(turn)
            asyncio.create_task(
                self._save_turn_to_db(
                    turn.turn_number,
                    turn.turn_type.value,
                    turn.content,
                    character_name=turn.character_name,
                    bgm_scene=turn.bgm_scene,
                )
            )

            if seg.type == StoryTurnType.CHOICE_PROMPT:
                # Parse options from content
                options = []
                import re

                for line in seg.content.split("\n"):
                    match = re.match(r"^\d+[.、]\s*(.+)$", line.strip())
                    if match:
                        options.append(match.group(1))

                # Remove options from prompt text
                prompt_text = seg.content.split("\n")[0] if "\n" in seg.content else seg.content

                sent = await self._safe_send_json(
                    {
                        "type": StoryMessageType.CHOICE_PROMPT,
                        "data": {
                            "prompt": prompt_text,
                            "options": options,
                            "context": "",
                        },
                    }
                )
                if not sent:
                    return
            else:
                if not self.is_connected:
                    return
                audio_b64 = await self._synthesize_segment(seg, chars)
                sent = await self._safe_send_json(
                    {
                        "type": StoryMessageType.STORY_SEGMENT,
                        "data": {
                            "turn_type": seg.type.value,
                            "content": seg.content,
                            "character_name": seg.character_name,
                            "emotion": seg.emotion,
                            "scene": seg.scene,
                            "audio": audio_b64,
                            "audio_format": "mp3" if audio_b64 else None,
                        },
                    }
                )
                if not sent:
                    return

            # Small delay between segments for natural pacing
            if len(segments) > 1:
                await asyncio.sleep(0.3)

        # Update session summary
        if self._session and segments:
            last_content = segments[-1].content[:100]
            self._session.story_state["summary"] = last_content

        # Signal story end if complete
        if is_complete and self.is_connected:
            await self._safe_send_json({"type": StoryMessageType.STORY_END, "data": {}})

    async def _load_template_from_db(self, template_id: str) -> StoryTemplate | None:
        """Load a StoryTemplate entity from DB via repository. Returns None if not found."""
        from uuid import UUID as _UUID

        try:
            repo = self._repo_factory()
            m = await repo.get_template(_UUID(template_id))
            if not m:
                return None
            return StoryTemplate(
                id=m.id,
                name=m.name,
                description=m.description,
                category=m.category,
                target_age_min=m.target_age_min,
                target_age_max=m.target_age_max,
                language=m.language,
                characters=[StoryCharacter(**c) for c in (m.characters or [])],
                scenes=[SceneInfo(**s) for s in (m.scenes or [])],
                opening_prompt=m.opening_prompt,
                system_prompt=m.system_prompt,
                is_default=m.is_default,
            )
        except Exception as exc:
            self._logger.warning("Failed to load template %s from DB: %s", template_id, exc)
            return None

    async def _create_db_session(
        self,
        session_id: UUID,
        template_id: UUID | None,
        title: str,
        language: str,
        system_prompt: str,
        chars: list[StoryCharacter],
    ) -> UUID | None:
        """Create a DB session via repository. Returns the DB session ID."""
        try:
            chars_data = [dataclasses.asdict(c) for c in chars]
            repo = self._repo_factory()
            db_obj = await repo.create_session(
                {
                    "id": session_id,
                    "user_id": self._user_id,
                    "template_id": template_id,
                    "title": title,
                    "language": language,
                    "status": "active",
                    "story_state": {"system_prompt": system_prompt},
                    "characters_config": chars_data,
                }
            )
            return db_obj.id
        except Exception as exc:
            self._logger.warning("Failed to create DB session: %s", exc)
            return None

    async def _save_turn_to_db(
        self,
        turn_number: int,
        turn_type: str,
        content: str,
        character_name: str | None = None,
        bgm_scene: str | None = None,
        child_choice: str | None = None,
    ) -> None:
        """Fire-and-forget: persist a story turn to DB. DB failure never breaks WS."""
        if not self._db_session_id:
            return
        try:
            repo = self._repo_factory()
            await repo.add_turn(
                {
                    "session_id": self._db_session_id,
                    "turn_number": turn_number,
                    "turn_type": turn_type,
                    "content": content,
                    "character_name": character_name,
                    "bgm_scene": bgm_scene,
                    "child_choice": child_choice,
                }
            )
        except Exception as exc:
            self._logger.debug("Failed to save turn %d to DB: %s", turn_number, exc)

    async def _update_db_session_status(self, status: str) -> None:
        """Update the DB session status (e.g. 'paused' on disconnect)."""
        if not self._db_session_id:
            return
        try:
            repo = self._repo_factory()
            await repo.update_session(
                session_id=self._db_session_id,
                user_id=self._user_id,
                updates={"status": status},
            )
        except Exception as exc:
            self._logger.warning("Failed to update DB session status: %s", exc)
