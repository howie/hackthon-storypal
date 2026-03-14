"""Gemini TTS Provider using Google GenAI SDK.

Implements TTS synthesis using Gemini 2.5 TTS models with support for:
- 30 prebuilt voices
- Natural language style prompts for voice control
- PCM to MP3/WAV/OGG conversion
"""

import asyncio
import io
import logging
import os
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types
from pydub import AudioSegment

from src.domain.entities.audio import AudioData, AudioFormat
from src.domain.entities.tts import TTSRequest
from src.domain.entities.voice import Gender, VoiceProfile
from src.domain.errors import QuotaExceededError, RateLimitError
from src.infrastructure.providers.tts.base import BaseTTSProvider

logger = logging.getLogger(__name__)

# Module-level request semaphore shared across all GeminiTTSProvider instances.
# Controls max concurrent requests to Gemini TTS API to avoid 429 rate limits.
_GEMINI_MAX_CONCURRENT = int(os.getenv("GEMINI_TTS_MAX_CONCURRENT", "5"))
_gemini_request_semaphore = asyncio.Semaphore(_GEMINI_MAX_CONCURRENT)


class GeminiTTSProvider(BaseTTSProvider):
    """Gemini TTS provider using Google GenAI SDK.

    Features:
    - Models: gemini-2.5-pro-preview-tts (high quality), gemini-2.5-flash-preview-tts (low latency)
    - 30 prebuilt voices with multilingual support
    - Natural language style prompts for emotional/stylistic control
    - Output: PCM 24kHz (converted to MP3/WAV/OGG)
    - Limits: Input max 4000 bytes, output max ~655 seconds
    """

    # Gemini TTS input limit is 4000 bytes (not characters).
    # CJK characters are 3 bytes each in UTF-8, so ~1333 characters max.
    GEMINI_MAX_INPUT_BYTES = 4000

    # Retry config for transient finishReason=OTHER errors
    _MAX_RETRIES = 2  # total attempts = _MAX_RETRIES + 1
    _RETRY_BACKOFFS = (0.5, 1.0)

    # Retry config for 429 rate limit errors (independent counter)
    _MAX_429_RETRIES = 3
    _429_RETRY_BACKOFFS = (1.0, 2.0, 4.0)

    # Gemini voices curated for Taiwanese Chinese (台灣中文).
    # Based on Google official descriptions and Chinese voice quality testing.
    # Each voice includes: gender, description (特色 · 場景), sample_text (角色台詞).
    VOICES: dict[str, dict[str, str]] = {
        # ── Female voices ────────────────────────────────────────
        "Kore": {
            "gender": "female",
            "description": "堅定自信 · 企業、品牌",
            "sample_text": "各位股東大家好，很高興在此向各位報告本季的營運成果，整體表現超出預期。",
        },
        "Aoede": {
            "gender": "female",
            "description": "旋律優雅 · 文學朗讀",
            "sample_text": "那年春天，櫻花沿著河岸一路盛開，空氣中瀰漫著淡淡的花香。",
        },
        "Leda": {
            "gender": "female",
            "description": "年輕有活力 · 社群、短影片",
            "sample_text": "嗨大家好！今天要跟你們分享三個超實用的生活小技巧，趕快收藏起來！",
        },
        "Sulafat": {
            "gender": "female",
            "description": "溫暖歡迎 · 接待、引導",
            "sample_text": "歡迎光臨，請問今天想體驗哪一項服務呢？讓我為您介紹。",
        },
        "Vindemiatrix": {
            "gender": "female",
            "description": "溫柔善良 · 療癒、陪伴",
            "sample_text": "沒關係的，每個人都有累的時候，好好休息一下，明天又是新的開始。",
        },
        "Laomedeia": {
            "gender": "female",
            "description": "開朗活潑 · 兒童內容、娛樂",
            "sample_text": "小朋友們，你們準備好了嗎？今天我們要一起去森林裡探險囉！",
        },
        "Achernar": {
            "gender": "female",
            "description": "柔和溫柔 · 睡前故事、ASMR",
            "sample_text": "夜深了，星星在天空中閃爍，月光輕輕灑在窗台上，一切都安靜了下來。",
        },
        "Erinome": {
            "gender": "female",
            "description": "清晰精確 · 專業報告",
            "sample_text": "根據最新的市場調查數據顯示，本季度消費者信心指數較上季成長百分之五。",
        },
        # ── Male voices ──────────────────────────────────────────
        "Charon": {
            "gender": "male",
            "description": "資訊清晰 · 新聞播報、教學",
            "sample_text": "今天的頭條新聞，中央氣象署發布豪雨特報，請各地民眾注意安全。",
        },
        "Puck": {
            "gender": "male",
            "description": "活潑有勁 · 通用",
            "sample_text": "哈囉！歡迎收聽今天的節目，我們準備了很多精彩的內容要跟大家分享！",
        },
        "Fenrir": {
            "gender": "male",
            "description": "興奮活潑 · 遊戲、娛樂",
            "sample_text": "太厲害了！恭喜你通過最終關卡，成為傳說中的勇者！",
        },
        "Schedar": {
            "gender": "male",
            "description": "關懷支持 · 醫療、諮詢",
            "sample_text": "別擔心，我們會一步一步陪您走過這段路程，您的健康是我們最重要的事。",
        },
        "Umbriel": {
            "gender": "male",
            "description": "神秘引人 · 懸疑、故事",
            "sample_text": "那扇門後面，究竟藏著什麼秘密？沒有人知道，也沒有人敢打開。",
        },
        "Gacrux": {
            "gender": "male",
            "description": "成熟穩重 · 紀錄片、財經",
            "sample_text": "回顧過去二十年的發展歷程，台灣半導體產業已成為全球供應鏈的關鍵力量。",
        },
        "Achird": {
            "gender": "male",
            "description": "友善親切 · 客服、助理",
            "sample_text": "您好，感謝您的來電，請問有什麼我可以幫您的嗎？",
        },
        "Iapetus": {
            "gender": "male",
            "description": "清楚流利 · 教學、說明",
            "sample_text": "接下來我們來看第三個步驟，請大家打開課本第四十二頁。",
        },
        "Orus": {
            "gender": "male",
            "description": "堅定果斷 · 決策、指揮",
            "sample_text": "時間緊迫，我們必須立刻做出決定。各單位請立即回報準備狀況。",
        },
        "Sadachbia": {
            "gender": "male",
            "description": "生動有趣 · 動畫、兒童",
            "sample_text": "哇！你看那隻小兔子跳得好高呀，牠是不是想飛到月亮上去呢？",
        },
    }

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-pro-preview-tts",
        fallback_model: str | None = None,
    ):
        """Initialize Gemini TTS provider.

        Args:
            api_key: Google AI API key
            model: Model to use (gemini-2.5-pro-preview-tts or gemini-2.5-flash-preview-tts)
            fallback_model: Optional fallback model when primary RPD quota is exhausted
        """
        super().__init__("gemini")
        self._api_key = api_key
        self._model = model
        self._fallback_model = fallback_model or None  # Treat empty string as None
        self._primary_quota_exhausted = False
        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _validate_input_byte_length(text_content: str) -> None:
        """Validate that text_content does not exceed Gemini's byte limit.

        Gemini TTS API limits input to 4000 bytes (UTF-8). CJK characters
        use 3 bytes each, so the character limit varies by language.

        Args:
            text_content: The full text to send (including style prompt if any).

        Raises:
            ValueError: If text exceeds the byte limit.
        """
        byte_length = len(text_content.encode("utf-8"))
        if byte_length > GeminiTTSProvider.GEMINI_MAX_INPUT_BYTES:
            char_length = len(text_content)
            raise ValueError(
                f"Gemini TTS input exceeds the {GeminiTTSProvider.GEMINI_MAX_INPUT_BYTES}-byte limit: "
                f"{byte_length} bytes ({char_length} characters). "
                "CJK characters use 3 bytes each. Please shorten the text or split into smaller segments."
            )

    async def _do_synthesize(self, request: TTSRequest) -> AudioData:
        """Synthesize speech using Gemini TTS API with automatic model fallback.

        When a fallback_model is configured, this method will:
        1. Skip the primary model if its daily quota is already known to be exhausted
        2. Catch QuotaExceededError from the primary model and retry with the fallback
        3. Raise QuotaExceededError only when both models are exhausted

        Args:
            request: TTS synthesis request

        Returns:
            AudioData with synthesized audio
        """
        # Determine which model to use
        active_model = self._model
        if self._primary_quota_exhausted and self._fallback_model:
            active_model = self._fallback_model

        try:
            return await self._synthesize_with_model(active_model, request)
        except QuotaExceededError:
            if active_model == self._model and self._fallback_model:
                # Primary exhausted → try fallback
                logger.warning(
                    "gemini_tts_model_fallback: primary=%s -> fallback=%s, reason=rpd_exhausted",
                    self._model,
                    self._fallback_model,
                )
                self._primary_quota_exhausted = True
                return await self._synthesize_with_model(self._fallback_model, request)
            raise  # Fallback also exhausted or no fallback configured

    async def _synthesize_with_model(self, model: str, request: TTSRequest) -> AudioData:
        """Synthesize speech using a specific Gemini TTS model via GenAI SDK.

        Args:
            model: Gemini model name to use for synthesis
            request: TTS synthesis request

        Returns:
            AudioData with synthesized audio
        """
        # Build text content with optional style prompt
        text_content = request.text
        if request.style_prompt:
            text_content = f"{request.style_prompt}: {request.text}"

        # Validate byte-level input length before calling API
        self._validate_input_byte_length(text_content)

        # Extract voice name - strip provider prefix if present (e.g., "gemini:Kore" -> "Kore")
        voice_name = request.voice_id
        if voice_name.startswith("gemini:"):
            voice_name = voice_name[7:]  # Remove "gemini:" prefix

        logger.debug(
            "Gemini TTS request: model=%s, voice_id=%s -> voice_name=%s, text_len=%d, style=%s",
            model,
            request.voice_id,
            voice_name,
            len(text_content),
            request.style_prompt or "(none)",
        )

        # Build GenAI SDK config for TTS
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )

        # Retry loop for transient finishReason=OTHER errors
        last_error: ValueError | None = None
        byte_length = len(text_content.encode("utf-8"))
        char_length = len(text_content)
        for attempt in range(self._MAX_RETRIES + 1):
            # Inner retry loop for 429 rate limiting (independent counter)
            for retry_429 in range(self._MAX_429_RETRIES + 1):
                try:
                    async with _gemini_request_semaphore:
                        response = await self._client.aio.models.generate_content(
                            model=model,
                            contents=text_content,
                            config=config,
                        )
                    break  # Success, exit 429 retry loop
                except Exception as e:
                    error_message = str(e)

                    # Detect 429 rate limit errors
                    if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                        # Detect daily quota exhaustion — retrying won't help
                        if "per_day" in error_message.lower():
                            logger.warning(
                                "Gemini TTS daily quota exhausted: model=%s, %s",
                                model,
                                error_message,
                            )
                            raise QuotaExceededError(
                                provider="gemini",
                                original_error=error_message,
                            ) from e

                        if retry_429 < self._MAX_429_RETRIES:
                            wait = self._429_RETRY_BACKOFFS[retry_429]
                            logger.warning(
                                "Gemini TTS RPM rate limited on attempt %d/%d, "
                                "retrying after %.1fs: %s",
                                retry_429 + 1,
                                self._MAX_429_RETRIES + 1,
                                wait,
                                error_message,
                            )
                            await asyncio.sleep(wait)
                            continue

                        # All 429 retries exhausted
                        raise RateLimitError(
                            provider="gemini",
                            retry_after=None,
                            original_error=error_message,
                        ) from e

                    # Detect quota exhaustion in other error types
                    if "exceeded your current quota" in error_message.lower():
                        raise QuotaExceededError(
                            provider="gemini",
                            original_error=error_message,
                        ) from e

                    raise RuntimeError(f"Gemini TTS API error: {error_message}") from e
            else:
                # 429 retry loop exhausted without break
                raise RateLimitError(
                    provider="gemini",
                    retry_after=None,
                    original_error="429 retries exhausted",
                )

            # Check for empty or blocked candidates
            if not response.candidates:
                logger.error("Gemini TTS returned no candidates")
                raise ValueError(
                    "Gemini TTS returned no candidates. "
                    "The input may have been blocked by safety filters."
                )

            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason

            # Detect safety-blocked responses (candidates exist but no content)
            if not candidate.content:
                if str(finish_reason) == "SAFETY":
                    raise ValueError(
                        "Gemini TTS blocked the request due to safety filters. "
                        "Try rephrasing the text or using a different style prompt."
                    )

                # finishReason=OTHER may be transient — retry
                logger.warning(
                    "Gemini TTS finishReason=%s on attempt %d/%d (text: %d bytes, %d chars)",
                    finish_reason,
                    attempt + 1,
                    self._MAX_RETRIES + 1,
                    byte_length,
                    char_length,
                )
                last_error = ValueError(
                    f"Gemini TTS returned no audio content (finishReason={finish_reason}). "
                    "This may be caused by Gemini's internal safety filters (e.g. PII detection). "
                    "Try avoiding personal names, addresses, phone numbers, or other "
                    "personally identifiable information in the text."
                )
                if attempt < self._MAX_RETRIES:
                    await asyncio.sleep(self._RETRY_BACKOFFS[attempt])
                    continue
                raise last_error

            # Extract audio data from response
            try:
                parts = candidate.content.parts
                if not parts:
                    raise IndexError("No parts in response")
                part = parts[0]
                pcm_data = part.inline_data.data  # type: ignore[union-attr]
            except (AttributeError, IndexError) as e:
                logger.error("Unexpected Gemini TTS response structure: %s", candidate)
                raise ValueError(f"Invalid API response structure: {e}") from e

            # Convert PCM to target format
            audio_data = await self._convert_pcm_to_format(pcm_data, request.output_format)

            return AudioData(
                data=audio_data,
                format=request.output_format,
                sample_rate=24000,
            )

        # Should not reach here, but just in case
        raise last_error  # type: ignore[misc]

    async def _convert_pcm_to_format(self, pcm_data: bytes, target_format: AudioFormat) -> bytes:
        """Convert PCM 24kHz to target audio format.

        Args:
            pcm_data: Raw PCM audio data (16-bit, 24kHz, mono)
            target_format: Target audio format

        Returns:
            Converted audio data
        """
        # Create AudioSegment from raw PCM data
        audio = AudioSegment(
            data=pcm_data,
            sample_width=2,  # 16-bit
            frame_rate=24000,
            channels=1,
        )

        buffer = io.BytesIO()
        format_map = {
            AudioFormat.MP3: "mp3",
            AudioFormat.WAV: "wav",
            AudioFormat.OGG: "ogg",
            AudioFormat.OPUS: "opus",
            AudioFormat.FLAC: "flac",
        }
        export_format = format_map.get(target_format, "mp3")
        audio.export(buffer, format=export_format)
        return buffer.getvalue()

    async def synthesize_stream(self, request: TTSRequest) -> AsyncGenerator[bytes, None]:
        """Synthesize speech with streaming output.

        Note: Gemini TTS doesn't support native streaming, so this synthesizes
        the complete audio and yields it in chunks.

        Args:
            request: TTS synthesis request

        Yields:
            Audio data chunks
        """
        audio = await self._do_synthesize(request)
        # Yield in 32KB chunks for streaming simulation
        chunk_size = 32768
        for i in range(0, len(audio.data), chunk_size):
            yield audio.data[i : i + chunk_size]

    async def list_voices(self, language: str | None = None) -> list[VoiceProfile]:
        """List available Gemini voices.

        Args:
            language: Optional language filter (Gemini voices are multilingual)

        Returns:
            List of available voice profiles
        """
        voices = []
        for voice_id, info in self.VOICES.items():
            voices.append(
                VoiceProfile(
                    id=f"gemini:{voice_id}",
                    provider="gemini",
                    voice_id=voice_id,
                    display_name=voice_id,
                    language=language or "zh-TW",
                    gender=Gender.MALE if info["gender"] == "male" else Gender.FEMALE,
                    description=info["description"],
                    metadata={
                        "description_zh": info["description"],
                        "sample_text": info.get("sample_text", ""),
                    },
                )
            )
        return voices

    async def get_voice(self, voice_id: str) -> VoiceProfile | None:
        """Get a specific voice profile.

        Args:
            voice_id: Voice identifier (can be "Kore" or "gemini:Kore")

        Returns:
            Voice profile if found, None otherwise
        """
        # Strip provider prefix if present
        lookup_id = voice_id
        if lookup_id.startswith("gemini:"):
            lookup_id = lookup_id[7:]

        if lookup_id in self.VOICES:
            info = self.VOICES[lookup_id]
            return VoiceProfile(
                id=f"gemini:{lookup_id}",
                provider="gemini",
                voice_id=lookup_id,
                display_name=lookup_id,
                language="zh-TW",
                gender=Gender.MALE if info["gender"] == "male" else Gender.FEMALE,
                description=info["description"],
                metadata={
                    "description_zh": info["description"],
                    "sample_text": info.get("sample_text", ""),
                },
            )
        return None

    def get_supported_params(self) -> dict:
        """Get supported parameters and their valid ranges.

        Note: Gemini TTS uses style prompts for control instead of
        traditional speed/pitch/volume parameters.

        Returns:
            Dictionary with parameter names and their constraints
        """
        return {
            "speed": {"min": 0.5, "max": 2.0, "default": 1.0, "note": "Use style prompt"},
            "pitch": {"min": -20.0, "max": 20.0, "default": 0.0, "note": "Use style prompt"},
            "volume": {"min": 0.0, "max": 2.0, "default": 1.0, "note": "Use style prompt"},
            "style_prompt": {
                "type": "string",
                "default": None,
                "description": "Natural language prompt for voice style control",
                "examples": [
                    "Say this cheerfully with excitement",
                    "Speak slowly and calmly",
                    "Use a professional news anchor tone",
                ],
            },
        }

    async def health_check(self) -> bool:
        """Check API connectivity.

        Returns:
            True if API is accessible
        """
        if not self._api_key:
            return False

        try:
            # Lightweight check — list models to verify API key works
            # Avoid generate_content as it consumes real quota on every health check
            async for _ in await self._client.aio.models.list(config={"page_size": 1}):
                break
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the GenAI client."""
        # GenAI SDK client doesn't require explicit close for sync usage,
        # but we keep the method for interface compatibility.
        pass
