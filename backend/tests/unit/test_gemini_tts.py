"""Unit tests for Gemini TTS provider (GenAI SDK).

Tests for the Gemini TTS provider implementation including:
- Voice listing and retrieval
- Synthesis with style prompts
- PCM to audio format conversion
- Health check functionality
- Error code routing (GenAI SDK exceptions → correct exception)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities.audio import AudioFormat, OutputMode
from src.domain.entities.tts import TTSRequest
from src.domain.entities.voice import Gender
from src.domain.errors import QuotaExceededError, RateLimitError
from src.infrastructure.providers.tts.gemini_tts import GeminiTTSProvider


@pytest.fixture
def gemini_provider() -> GeminiTTSProvider:
    """Create a Gemini TTS provider for testing."""
    return GeminiTTSProvider(api_key="test-api-key")


@pytest.fixture
def sample_request() -> TTSRequest:
    """Create a sample TTS request for testing."""
    return TTSRequest(
        text="Hello, this is a test.",
        voice_id="Kore",
        provider="gemini",
        language="zh-TW",
        speed=1.0,
        pitch=0.0,
        volume=1.0,
        output_format=AudioFormat.MP3,
        output_mode=OutputMode.BATCH,
    )


@pytest.fixture
def sample_request_with_style() -> TTSRequest:
    """Create a sample TTS request with style prompt."""
    return TTSRequest(
        text="Hello, this is a test.",
        voice_id="Kore",
        provider="gemini",
        language="zh-TW",
        speed=1.0,
        pitch=0.0,
        volume=1.0,
        output_format=AudioFormat.MP3,
        output_mode=OutputMode.BATCH,
        style_prompt="Say this cheerfully with excitement",
    )


def _make_sdk_tts_response(pcm_data: bytes | None = None) -> MagicMock:
    """Create a mock GenAI SDK generate_content response for TTS."""
    if pcm_data is None:
        pcm_data = b"\x00\x00" * 24000  # 1 second of silence

    mock_inline_data = MagicMock()
    mock_inline_data.data = pcm_data

    mock_part = MagicMock()
    mock_part.inline_data = mock_inline_data

    mock_content = MagicMock()
    mock_content.parts = [mock_part]

    mock_candidate = MagicMock()
    mock_candidate.content = mock_content
    mock_candidate.finish_reason = "STOP"

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    return mock_response


def _make_sdk_empty_response() -> MagicMock:
    """Create a mock response with no candidates."""
    mock_response = MagicMock()
    mock_response.candidates = []
    return mock_response


def _make_sdk_safety_response() -> MagicMock:
    """Create a mock response blocked by safety filters."""
    mock_candidate = MagicMock()
    mock_candidate.content = None
    mock_candidate.finish_reason = "SAFETY"

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    return mock_response


def _make_sdk_other_response() -> MagicMock:
    """Create a mock response with finishReason=OTHER (transient error)."""
    mock_candidate = MagicMock()
    mock_candidate.content = None
    mock_candidate.finish_reason = "OTHER"

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    return mock_response


class TestGeminiTTSProvider:
    """Tests for Gemini TTS provider."""

    def test_provider_name(self, gemini_provider: GeminiTTSProvider):
        """Test provider name property."""
        assert gemini_provider.name == "gemini"

    def test_display_name(self, gemini_provider: GeminiTTSProvider):
        """Test display name property."""
        assert gemini_provider.display_name == "Gemini TTS"

    def test_supported_formats(self, gemini_provider: GeminiTTSProvider):
        """Test supported audio formats."""
        formats = gemini_provider.supported_formats
        assert AudioFormat.MP3 in formats
        assert AudioFormat.WAV in formats
        assert AudioFormat.OGG in formats

    def test_default_model(self):
        """Test default model is set correctly."""
        provider = GeminiTTSProvider(api_key="test-key")
        assert provider._model == "gemini-2.5-pro-preview-tts"

    def test_custom_model(self):
        """Test custom model can be specified."""
        provider = GeminiTTSProvider(
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
        )
        assert provider._model == "gemini-2.5-flash-preview-tts"

    @pytest.mark.asyncio
    async def test_list_voices_all(self, gemini_provider: GeminiTTSProvider):
        """Test listing all voices."""
        voices = await gemini_provider.list_voices()

        assert len(voices) == 18  # 18 voices curated for Taiwanese Chinese
        assert all(v.provider == "gemini" for v in voices)

    @pytest.mark.asyncio
    async def test_list_voices_with_language(self, gemini_provider: GeminiTTSProvider):
        """Test listing voices with language filter."""
        voices = await gemini_provider.list_voices(language="zh-TW")

        assert len(voices) == 18
        assert all(v.language == "zh-TW" for v in voices)

    @pytest.mark.asyncio
    async def test_list_voices_zh_tw_default(self, gemini_provider: GeminiTTSProvider):
        """Test voices default to zh-TW when no language specified."""
        voices = await gemini_provider.list_voices()

        assert all(v.language == "zh-TW" for v in voices)

    @pytest.mark.asyncio
    async def test_get_voice_exists(self, gemini_provider: GeminiTTSProvider):
        """Test getting a specific voice that exists."""
        voice = await gemini_provider.get_voice("Kore")

        assert voice is not None
        assert voice.voice_id == "Kore"
        assert voice.display_name == "Kore"
        assert voice.gender == Gender.FEMALE
        assert "堅定自信" in voice.description

    @pytest.mark.asyncio
    async def test_get_voice_not_found(self, gemini_provider: GeminiTTSProvider):
        """Test getting a voice that doesn't exist."""
        voice = await gemini_provider.get_voice("non-existent-voice")

        assert voice is None

    def test_get_supported_params(self, gemini_provider: GeminiTTSProvider):
        """Test getting supported parameter ranges."""
        params = gemini_provider.get_supported_params()

        assert "speed" in params
        assert "pitch" in params
        assert "volume" in params
        assert "style_prompt" in params
        assert params["style_prompt"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_health_check_configured(self, gemini_provider: GeminiTTSProvider):
        """Test health check when properly configured."""

        async def _fake_list(*args, **kwargs):
            yield MagicMock()

        mock_list = AsyncMock(return_value=_fake_list())
        with patch.object(gemini_provider._client.aio.models, "list", mock_list):
            is_healthy = await gemini_provider.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self):
        """Test health check when not configured (empty API key)."""
        # GenAI SDK rejects empty API keys at client init,
        # so we test via the property check instead
        provider = GeminiTTSProvider(api_key="dummy-key-for-init")
        provider._api_key = ""  # Override after init to simulate missing key
        is_healthy = await provider.health_check()
        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_api_error(self, gemini_provider: GeminiTTSProvider):
        """Test health check when API returns error."""
        mock_list = AsyncMock(side_effect=Exception("Connection error"))
        with patch.object(gemini_provider._client.aio.models, "list", mock_list):
            is_healthy = await gemini_provider.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_synthesize_success(
        self, gemini_provider: GeminiTTSProvider, sample_request: TTSRequest
    ):
        """Test successful synthesis."""
        mock_mp3_data = b"mock-mp3-audio-data"

        mock_generate = AsyncMock(return_value=_make_sdk_tts_response())
        with (
            patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate),
            patch.object(
                gemini_provider, "_convert_pcm_to_format", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_convert.return_value = mock_mp3_data

            result = await gemini_provider.synthesize(sample_request)

            assert result is not None
            assert result.audio.data is not None
            assert len(result.audio.data) > 0
            assert result.audio.format == AudioFormat.MP3

    @pytest.mark.asyncio
    async def test_synthesize_with_style_prompt(
        self, gemini_provider: GeminiTTSProvider, sample_request_with_style: TTSRequest
    ):
        """Test synthesis with style prompt."""
        mock_mp3_data = b"mock-mp3-audio-data"

        mock_generate = AsyncMock(return_value=_make_sdk_tts_response())
        with (
            patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate),
            patch.object(
                gemini_provider, "_convert_pcm_to_format", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_convert.return_value = mock_mp3_data

            await gemini_provider.synthesize(sample_request_with_style)

            # Verify generate_content was called (style prompt is embedded in contents)
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_api_error(
        self, gemini_provider: GeminiTTSProvider, sample_request: TTSRequest
    ):
        """Test handling of API errors."""
        mock_generate = AsyncMock(
            side_effect=Exception("500 Internal Server Error: Model overloaded")
        )
        with patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(RuntimeError, match="Gemini TTS API error"):
                await gemini_provider.synthesize(sample_request)

    @pytest.mark.asyncio
    async def test_synthesize_stream(
        self, gemini_provider: GeminiTTSProvider, sample_request: TTSRequest
    ):
        """Test streaming synthesis."""
        mock_mp3_data = b"mock-mp3-audio-data"

        mock_generate = AsyncMock(return_value=_make_sdk_tts_response())
        with (
            patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate),
            patch.object(
                gemini_provider, "_convert_pcm_to_format", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_convert.return_value = mock_mp3_data

            chunks = []
            async for chunk in gemini_provider.synthesize_stream(sample_request):
                chunks.append(chunk)

            assert len(chunks) > 0
            assert all(isinstance(c, bytes) for c in chunks)


class TestGeminiVoices:
    """Tests for Gemini voice definitions."""

    def test_voices_have_required_fields(self):
        """Test all Gemini voices have required fields."""
        for _voice_id, info in GeminiTTSProvider.VOICES.items():
            assert "gender" in info
            assert "description" in info
            assert info["gender"] in ("male", "female")

    def test_expected_voices_exist(self):
        """Test expected voices are defined."""
        expected_voices = ["Kore", "Charon", "Aoede", "Puck", "Fenrir"]
        for voice in expected_voices:
            assert voice in GeminiTTSProvider.VOICES

    def test_voice_count(self):
        """Test correct number of voices defined."""
        assert len(GeminiTTSProvider.VOICES) == 18

    def test_kore_recommended_for_chinese(self):
        """Test Kore is recommended for Chinese with description and sample_text."""
        kore_info = GeminiTTSProvider.VOICES["Kore"]
        assert "堅定自信" in kore_info["description"]
        assert kore_info.get("sample_text"), "Kore should have a sample_text"


class TestGeminiByteValidation:
    """Tests for Gemini TTS byte-level input validation."""

    @pytest.mark.asyncio
    async def test_synthesize_byte_limit_cjk_text(self, gemini_provider: GeminiTTSProvider):
        """Test that CJK text exceeding 4000 bytes is rejected before API call."""
        # 1400 CJK characters × 3 bytes = 4200 bytes > 4000 limit
        long_cjk_text = "你" * 1400
        request = TTSRequest(
            text=long_cjk_text,
            voice_id="Kore",
            provider="gemini",
            language="zh-TW",
            speed=1.0,
            pitch=0.0,
            volume=1.0,
            output_format=AudioFormat.MP3,
            output_mode=OutputMode.BATCH,
        )

        with pytest.raises(ValueError, match="4000-byte limit"):
            await gemini_provider.synthesize(request)

    @pytest.mark.asyncio
    async def test_synthesize_byte_limit_with_style_prompt(
        self, gemini_provider: GeminiTTSProvider
    ):
        """Test that style_prompt + text combined byte count is validated."""
        # style_prompt (~40 bytes) + 1330 CJK chars (3990 bytes) + ": " (2 bytes) > 4000
        long_cjk_text = "你" * 1330
        request = TTSRequest(
            text=long_cjk_text,
            voice_id="Kore",
            provider="gemini",
            language="zh-TW",
            speed=1.0,
            pitch=0.0,
            volume=1.0,
            output_format=AudioFormat.MP3,
            output_mode=OutputMode.BATCH,
            style_prompt="Say this cheerfully with excitement",
        )

        with pytest.raises(ValueError, match="4000-byte limit"):
            await gemini_provider.synthesize(request)

    @pytest.mark.asyncio
    async def test_synthesize_byte_limit_within_limit(self, gemini_provider: GeminiTTSProvider):
        """Test that text within byte limit passes validation and calls API normally."""
        # 100 CJK characters × 3 bytes = 300 bytes, well within limit
        short_text = "你" * 100
        request = TTSRequest(
            text=short_text,
            voice_id="Kore",
            provider="gemini",
            language="zh-TW",
            speed=1.0,
            pitch=0.0,
            volume=1.0,
            output_format=AudioFormat.MP3,
            output_mode=OutputMode.BATCH,
        )

        mock_mp3_data = b"mock-mp3-audio-data"
        mock_generate = AsyncMock(return_value=_make_sdk_tts_response())

        with (
            patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate),
            patch.object(
                gemini_provider, "_convert_pcm_to_format", new_callable=AsyncMock
            ) as mock_convert,
        ):
            mock_convert.return_value = mock_mp3_data

            result = await gemini_provider.synthesize(request)
            assert result is not None
            assert result.audio.data == mock_mp3_data
            mock_generate.assert_called_once()


class TestGeminiFinishReasonRetry:
    """Tests for Gemini TTS finishReason=OTHER retry logic."""

    @pytest.mark.asyncio
    async def test_synthesize_finish_reason_other_retries_exhausted(
        self, gemini_provider: GeminiTTSProvider, sample_request: TTSRequest
    ):
        """Test that finishReason=OTHER retries 3 times then raises error."""
        mock_generate = AsyncMock(return_value=_make_sdk_other_response())

        with (
            patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(ValueError, match="finishReason=OTHER"):
                await gemini_provider.synthesize(sample_request)

            # Should have been called 3 times (1 initial + 2 retries)
            assert mock_generate.call_count == 3

    @pytest.mark.asyncio
    async def test_synthesize_finish_reason_other_succeeds_on_retry(
        self, gemini_provider: GeminiTTSProvider, sample_request: TTSRequest
    ):
        """Test that finishReason=OTHER succeeds on second attempt."""
        mock_mp3_data = b"mock-mp3-audio-data"
        mock_generate = AsyncMock(
            side_effect=[_make_sdk_other_response(), _make_sdk_tts_response()]
        )

        with (
            patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate),
            patch.object(
                gemini_provider, "_convert_pcm_to_format", new_callable=AsyncMock
            ) as mock_convert,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_convert.return_value = mock_mp3_data

            result = await gemini_provider.synthesize(sample_request)
            assert result is not None
            assert result.audio.data == mock_mp3_data
            assert mock_generate.call_count == 2

    @pytest.mark.asyncio
    async def test_synthesize_finish_reason_safety_no_retry(
        self, gemini_provider: GeminiTTSProvider, sample_request: TTSRequest
    ):
        """Test that finishReason=SAFETY does not retry and raises immediately."""
        mock_generate = AsyncMock(return_value=_make_sdk_safety_response())

        with patch.object(gemini_provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(ValueError, match="safety filters"):
                await gemini_provider.synthesize(sample_request)

            # Should only be called once — no retries for SAFETY
            assert mock_generate.call_count == 1


class TestGeminiErrorCodeRouting:
    """Tests that GenAI SDK exceptions are routed to the correct exception type."""

    @staticmethod
    def _make_gemini_request() -> TTSRequest:
        return TTSRequest(
            text="Test",
            voice_id="Kore",
            provider="gemini",
            output_format=AudioFormat.MP3,
            output_mode=OutputMode.BATCH,
        )

    @pytest.mark.asyncio
    async def test_general_error_raises_runtime_error(self) -> None:
        """General API errors raise RuntimeError."""
        provider = GeminiTTSProvider(api_key="test-key")
        mock_generate = AsyncMock(side_effect=Exception("500 Internal Server Error"))
        with patch.object(provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(RuntimeError, match="Gemini TTS API error"):
                await provider._do_synthesize(self._make_gemini_request())

    @pytest.mark.asyncio
    async def test_quota_exhausted_raises_quota_exceeded_error(self) -> None:
        """Quota exhaustion raises QuotaExceededError."""
        provider = GeminiTTSProvider(api_key="test-key")
        mock_generate = AsyncMock(
            side_effect=Exception("You exceeded your current quota, please check plan")
        )
        with patch.object(provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(QuotaExceededError):
                await provider._do_synthesize(self._make_gemini_request())

    @pytest.mark.asyncio
    async def test_429_per_day_raises_quota_exceeded_error(self) -> None:
        """429 per_day error raises QuotaExceededError (no retry)."""
        provider = GeminiTTSProvider(api_key="test-key")
        mock_generate = AsyncMock(
            side_effect=Exception("429 RESOURCE_EXHAUSTED: per_day limit reached")
        )
        with patch.object(provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(QuotaExceededError):
                await provider._do_synthesize(self._make_gemini_request())

    @pytest.mark.asyncio
    async def test_429_rpm_retries_then_raises_rate_limit_error(self) -> None:
        """429 RPM error retries and eventually raises RateLimitError."""
        provider = GeminiTTSProvider(api_key="test-key")
        mock_generate = AsyncMock(
            side_effect=Exception("429 RESOURCE_EXHAUSTED: rpm quota exceeded")
        )
        with (
            patch.object(provider._client.aio.models, "generate_content", mock_generate),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(RateLimitError):
                await provider._do_synthesize(self._make_gemini_request())

    @pytest.mark.asyncio
    async def test_200_empty_candidates_raises_value_error(self) -> None:
        """Response with no candidates raises ValueError."""
        provider = GeminiTTSProvider(api_key="test-key")
        mock_generate = AsyncMock(return_value=_make_sdk_empty_response())
        with patch.object(provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(ValueError, match="no candidates"):
                await provider._do_synthesize(self._make_gemini_request())


class TestGeminiTTSModelFallback:
    """Tests for Gemini TTS model fallback (Pro → Flash on RPD exhaustion)."""

    @staticmethod
    def _make_request() -> TTSRequest:
        return TTSRequest(
            text="Test fallback",
            voice_id="Kore",
            provider="gemini",
            output_format=AudioFormat.MP3,
            output_mode=OutputMode.BATCH,
        )

    @pytest.mark.asyncio
    async def test_fallback_on_quota_exhausted(self) -> None:
        """Primary model returns QuotaExceededError → fallback model succeeds."""
        provider = GeminiTTSProvider(
            api_key="test-key",
            model="gemini-2.5-pro-preview-tts",
            fallback_model="gemini-2.5-flash-preview-tts",
        )

        # First call raises quota error, second succeeds
        mock_generate = AsyncMock(
            side_effect=[
                Exception("429 RESOURCE_EXHAUSTED: per_day limit"),
                _make_sdk_tts_response(),
            ]
        )

        mock_mp3 = b"mock-mp3"
        with (
            patch.object(provider._client.aio.models, "generate_content", mock_generate),
            patch.object(provider, "_convert_pcm_to_format", new_callable=AsyncMock) as mock_conv,
        ):
            mock_conv.return_value = mock_mp3
            result = await provider._do_synthesize(self._make_request())

        assert result.data == mock_mp3
        assert provider._primary_quota_exhausted is True

    @pytest.mark.asyncio
    async def test_fallback_stays_on_fallback_model(self) -> None:
        """After primary exhaustion, subsequent requests go directly to fallback."""
        provider = GeminiTTSProvider(
            api_key="test-key",
            model="gemini-2.5-pro-preview-tts",
            fallback_model="gemini-2.5-flash-preview-tts",
        )
        provider._primary_quota_exhausted = True  # Simulate prior exhaustion

        mock_generate = AsyncMock(return_value=_make_sdk_tts_response())

        mock_mp3 = b"mock-mp3"
        with (
            patch.object(provider._client.aio.models, "generate_content", mock_generate),
            patch.object(provider, "_convert_pcm_to_format", new_callable=AsyncMock) as mock_conv,
        ):
            mock_conv.return_value = mock_mp3
            result = await provider._do_synthesize(self._make_request())

        assert result.data == mock_mp3
        # Should have called only once (directly to fallback, not trying primary)
        assert mock_generate.call_count == 1

    @pytest.mark.asyncio
    async def test_both_models_exhausted_raises(self) -> None:
        """Both primary and fallback exhausted → raises QuotaExceededError."""
        provider = GeminiTTSProvider(
            api_key="test-key",
            model="gemini-2.5-pro-preview-tts",
            fallback_model="gemini-2.5-flash-preview-tts",
        )

        mock_generate = AsyncMock(side_effect=Exception("429 RESOURCE_EXHAUSTED: per_day limit"))

        with patch.object(provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(QuotaExceededError):
                await provider._do_synthesize(self._make_request())

        assert provider._primary_quota_exhausted is True

    @pytest.mark.asyncio
    async def test_no_fallback_configured(self) -> None:
        """No fallback model → QuotaExceededError propagates as before."""
        provider = GeminiTTSProvider(
            api_key="test-key",
            model="gemini-2.5-pro-preview-tts",
            fallback_model=None,
        )

        mock_generate = AsyncMock(side_effect=Exception("429 RESOURCE_EXHAUSTED: per_day limit"))

        with patch.object(provider._client.aio.models, "generate_content", mock_generate):
            with pytest.raises(QuotaExceededError):
                await provider._do_synthesize(self._make_request())

        # No fallback → primary_quota_exhausted should NOT be set
        assert provider._primary_quota_exhausted is False
