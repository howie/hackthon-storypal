"""Google Gemini Live API client implementation using Google GenAI SDK.

Feature: 004-interaction-module
T027c: Gemini Live API client for V2V voice interaction.

Implements voice-to-voice interaction using Google's Gemini Live API
via the official GenAI SDK.
"""

import asyncio
import base64
import contextlib
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from google import genai
from google.genai import types

from src.domain.services.interaction.base import (
    AudioChunk,
    InteractionModeService,
    ResponseEvent,
)

logger = logging.getLogger(__name__)

# Available models for Gemini Live API (must support bidiGenerateContent)
# See: https://ai.google.dev/gemini-api/docs/models
# See: https://ai.google.dev/gemini-api/docs/live
AVAILABLE_MODELS = [
    "gemini-2.5-flash-native-audio-preview-12-2025",  # Newer preview, native audio + Chinese support
    "gemini-2.5-flash-native-audio-preview-09-2025",  # Older preview version
]

# Default configuration - use 2.5 native audio for Chinese support
DEFAULT_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_VOICE = "Kore"  # Female voice, good for Chinese


class GeminiRealtimeService(InteractionModeService):
    """Google Gemini Live API implementation using GenAI SDK.

    Provides voice-to-voice interaction using Gemini's Live API.

    The service manages:
    - Live API session via GenAI SDK
    - Audio streaming (input and output)
    - Turn management
    - Response generation and interruption
    """

    def __init__(self, api_key: str) -> None:
        """Initialize the service.

        Args:
            api_key: Google AI API key
        """
        self._api_key = api_key
        self._client = genai.Client(api_key=api_key)
        self._session: Any = None  # GenAI Live session
        self._live_ctx: Any = None  # async context manager for live.connect()
        self._session_id: UUID | None = None
        self._connected = False
        self._event_queue: asyncio.Queue[ResponseEvent] = asyncio.Queue()
        self._receive_task: asyncio.Task[None] | None = None
        self._config: dict[str, Any] = {}
        self._system_prompt = ""
        # Track accumulated transcripts to avoid duplicates
        self._accumulated_input_transcript = ""
        self._accumulated_output_transcript = ""
        self._setup_complete = False
        # Audio stats tracking
        self._reset_send_stats()
        self._reset_recv_stats()

    def _reset_send_stats(self) -> None:
        """Reset audio send statistics for a new turn."""
        self._send_chunk_count = 0
        self._send_bytes = 0

    def _reset_recv_stats(self) -> None:
        """Reset audio receive statistics for a new turn."""
        self._recv_chunk_count = 0
        self._recv_bytes = 0
        self._recv_first_chunk_time: float | None = None
        self._recv_start_time: float | None = None

    @property
    def mode_name(self) -> str:
        return "realtime"

    async def connect(
        self,
        session_id: UUID,
        config: dict[str, Any],
        system_prompt: str = "",
    ) -> None:
        """Connect to Gemini Live API via GenAI SDK.

        Args:
            session_id: Unique session identifier
            config: Provider configuration (model, voice, etc.)
            system_prompt: System instructions for the AI
        """
        self._session_id = session_id
        self._config = config
        self._system_prompt = system_prompt

        # Get model from config, fallback to settings, then default
        model = config.get("model")
        if not model:
            try:
                from src.config import get_settings

                settings = get_settings()
                model = settings.gemini_live_model
            except Exception:
                model = DEFAULT_MODEL

        voice = config.get("voice", DEFAULT_VOICE)

        # Build system instruction with Chinese language preamble
        chinese_language_preamble = (
            "[語言設定] 這是一個中文對話。"
            "請你全程使用繁體中文理解使用者的語音輸入，並用繁體中文回覆。"
            "即使使用者的語音被辨識為其他語言或有混合語言的情況，"
            "也請優先以繁體中文來理解和回應。\n\n"
        )
        base_prompt = (
            system_prompt
            or "你是一個親切的幼兒園老師，正在跟小朋友互動。請用溫柔、有耐心的方式說話，使用簡單易懂的詞彙。"
        )
        effective_prompt = chinese_language_preamble + base_prompt

        # Build Live API config
        live_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],  # type: ignore[list-item]
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
            system_instruction=types.Content(parts=[types.Part(text=effective_prompt)]),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            # Disable thinking for faster response (no internal reasoning delay)
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        logger.info(
            "Gemini setup: model=%s, voice=%s, prompt=%s",
            model,
            voice,
            (system_prompt[:100] + "...")
            if system_prompt and len(system_prompt) > 100
            else system_prompt or "(default)",
        )

        try:
            logger.info("Connecting to Gemini Live API via GenAI SDK...")
            # aio.live.connect() is an async context manager; we enter it manually
            # so the session stays open beyond this method. __aexit__ is called in disconnect().
            self._live_ctx = self._client.aio.live.connect(
                model=model,
                config=live_config,
            )
            self._session = await self._live_ctx.__aenter__()
            self._connected = True
            self._setup_complete = True

            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_messages())

            # Emit connected event
            await self._event_queue.put(
                ResponseEvent(
                    type="connected",
                    data={"status": "setup_complete"},
                )
            )

            logger.info("Connected to Gemini Live API for session %s", session_id)

        except Exception as e:
            logger.error("Failed to connect to Gemini Live API: %s", e)
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from the API and cleanup resources."""
        self._connected = False
        self._setup_complete = False

        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None

        # Close Live session via context manager exit
        if self._live_ctx:
            with contextlib.suppress(Exception):
                await self._live_ctx.__aexit__(None, None, None)
            self._live_ctx = None
            self._session = None

        self._session_id = None
        logger.info("Disconnected from Gemini Live API")

    async def send_audio(self, audio: AudioChunk) -> None:
        """Send audio data to the API.

        Args:
            audio: Audio chunk to stream to the API
        """
        if not self._connected or not self._session:
            logger.warning("Cannot send audio: not connected")
            return

        # Track send stats
        self._send_chunk_count += 1
        self._send_bytes += len(audio.data)

        # Send audio via GenAI SDK Live session
        sample_rate = audio.sample_rate or 16000
        mime_type = f"audio/pcm;rate={sample_rate}"

        await self._session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(
                        mime_type=mime_type,
                        data=audio.data,
                    )
                ]
            ),
        )

    async def send_text(self, text: str) -> None:
        """Send a text message to Gemini as user input.

        This allows sending text prompts during a V2V session.
        """
        if not self._connected or not self._session:
            logger.warning("Cannot send text: not connected")
            return

        logger.info("Gemini sending text input: %s", text[:100])
        await self._session.send(input=text, end_of_turn=True)

    async def end_turn(self) -> None:
        """Signal end of user speech.

        For Gemini Live API with realtime audio, we send an audio_stream_end
        signal to indicate the user has finished speaking.
        """
        if not self._connected or not self._session:
            return

        logger.info(
            "Gemini audio sent: %d chunks, %d bytes",
            self._send_chunk_count,
            self._send_bytes,
        )
        self._reset_send_stats()

        # Send end of audio stream
        await self._session.send(
            input=types.LiveClientRealtimeInput(audio_stream_end=True),
        )

    async def interrupt(self) -> None:
        """Interrupt the current AI response.

        Gemini handles interruption through client content.
        """
        if not self._connected or not self._session:
            return

        await self._session.send(input="", end_of_turn=True)
        logger.debug("Sent interrupt signal to Gemini")

    async def events(self) -> AsyncIterator[ResponseEvent]:
        """Async iterator for response events from Gemini.

        Yields ResponseEvent objects as they are received from the API.

        Note: Uses pure async wait without timeout to minimize latency.
        The loop exits when disconnected or cancelled.
        """
        while self._connected:
            try:
                event = await self._event_queue.get()
                yield event
            except asyncio.CancelledError:
                break

    def is_connected(self) -> bool:
        """Check if the service is connected."""
        return self._connected and self._session is not None and self._setup_complete

    async def _receive_messages(self) -> None:
        """Background task to receive and process messages from Gemini via GenAI SDK."""
        if not self._session:
            logger.warning("No session, exiting receive task")
            return

        try:
            async for message in self._session.receive():
                await self._handle_sdk_message(message)
            # Iterator ended normally (server closed session)
            logger.info("Gemini Live session receive loop ended normally")
            self._connected = False
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Error receiving Gemini messages: %s", e)
            self._connected = False

    async def _handle_sdk_message(self, message: Any) -> None:
        """Handle a message received from Gemini via GenAI SDK.

        Maps GenAI SDK Live API messages to our ResponseEvent format.
        """
        # The SDK returns LiveServerMessage objects with various fields
        server_content = getattr(message, "server_content", None)
        if server_content:
            # Handle input transcription
            input_transcription = getattr(server_content, "input_transcription", None)
            if input_transcription:
                text = getattr(input_transcription, "text", "")
                if text and text not in self._accumulated_input_transcript:
                    self._accumulated_input_transcript += text
                    await self._event_queue.put(
                        ResponseEvent(
                            type="transcript",
                            data={"text": text, "is_final": False},
                        )
                    )

            # Handle output transcription
            output_transcription = getattr(server_content, "output_transcription", None)
            if output_transcription:
                text = getattr(output_transcription, "text", "")
                if text and text not in self._accumulated_output_transcript:
                    self._accumulated_output_transcript += text
                    await self._event_queue.put(
                        ResponseEvent(
                            type="text_delta",
                            data={"delta": text},
                        )
                    )

            # Check for turn complete
            turn_complete = getattr(server_content, "turn_complete", False)
            if turn_complete:
                self._log_turn_summary()
                self._accumulated_input_transcript = ""
                self._accumulated_output_transcript = ""
                self._reset_recv_stats()
                await self._event_queue.put(
                    ResponseEvent(
                        type="response_ended",
                        data={"status": "complete"},
                    )
                )

            # Check for interruption
            interrupted = getattr(server_content, "interrupted", False)
            if interrupted:
                self._accumulated_input_transcript = ""
                self._accumulated_output_transcript = ""
                self._reset_recv_stats()
                await self._event_queue.put(
                    ResponseEvent(
                        type="interrupted",
                        data={"status": "interrupted"},
                    )
                )

            # Process model turn (audio/text content)
            model_turn = getattr(server_content, "model_turn", None)
            if model_turn:
                parts = getattr(model_turn, "parts", []) or []
                for part in parts:
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data:
                        mime_type = getattr(inline_data, "mime_type", "")
                        data = getattr(inline_data, "data", b"")
                        if mime_type and mime_type.startswith("audio/") and data:
                            # Track recv stats
                            now = time.monotonic()
                            self._recv_chunk_count += 1
                            data_b64 = base64.b64encode(data).decode()
                            self._recv_bytes += len(data_b64)
                            if self._recv_chunk_count == 1:
                                self._recv_start_time = now
                                self._recv_first_chunk_time = now
                                logger.info("Gemini audio recv started (%s)", mime_type)

                            await self._event_queue.put(
                                ResponseEvent(
                                    type="audio",
                                    data={
                                        "audio": data_b64,
                                        "format": "pcm16",
                                    },
                                )
                            )

                    text = getattr(part, "text", None)
                    if text:
                        await self._event_queue.put(
                            ResponseEvent(
                                type="text_delta",
                                data={"text": text},
                            )
                        )

        # Handle tool calls
        tool_call = getattr(message, "tool_call", None)
        if tool_call:
            function_calls = getattr(tool_call, "function_calls", []) or []
            await self._event_queue.put(
                ResponseEvent(
                    type="tool_call",
                    data={
                        "function_calls": [
                            {
                                "name": getattr(fc, "name", ""),
                                "args": getattr(fc, "args", {}),
                                "id": getattr(fc, "id", ""),
                            }
                            for fc in function_calls
                        ],
                    },
                )
            )

        # Handle tool call cancellation
        tool_call_cancellation = getattr(message, "tool_call_cancellation", None)
        if tool_call_cancellation:
            ids = getattr(tool_call_cancellation, "ids", []) or []
            await self._event_queue.put(
                ResponseEvent(
                    type="tool_call_cancelled",
                    data={"ids": ids},
                )
            )

    def _log_turn_summary(self) -> None:
        """Log a concise summary of the completed turn."""
        parts = []

        # Input transcript
        if self._accumulated_input_transcript:
            parts.append(f'input="{self._accumulated_input_transcript}"')

        # Output transcript
        if self._accumulated_output_transcript:
            out = self._accumulated_output_transcript
            parts.append(f"output={len(out)} chars")

        # Recv audio stats
        if self._recv_chunk_count > 0 and self._recv_start_time is not None:
            duration = time.monotonic() - self._recv_start_time
            first_chunk_ms = (
                (self._recv_first_chunk_time - self._recv_start_time) * 1000
                if self._recv_first_chunk_time and self._recv_start_time
                else 0
            )
            parts.append(
                f"recv_audio={self._recv_chunk_count} chunks/{self._recv_bytes} bytes/"
                f"{duration:.1f}s (first_chunk: {first_chunk_ms:.0f}ms)"
            )

        logger.info("Gemini turn complete: %s", ", ".join(parts) if parts else "(empty)")
