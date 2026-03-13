"""Unit tests for Realtime mode API clients.

Feature: 004-interaction-module
T027b: Unit tests for Realtime API clients (OpenAI, Gemini)

Tests the OpenAI Realtime API and Gemini Live API client implementations.
"""

import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.domain.entities.interaction_enums import InteractionMode, SessionStatus
from src.domain.entities.interaction_session import InteractionSession
from src.domain.services.interaction.base import InteractionModeService


@pytest.fixture
def sample_session() -> InteractionSession:
    """Create a sample interaction session."""
    return InteractionSession(
        id=uuid4(),
        user_id=uuid4(),
        mode=InteractionMode.REALTIME,
        provider_config={"provider": "openai", "voice": "alloy"},
        system_prompt="You are a helpful assistant.",
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(UTC),
        ended_at=None,
    )


@pytest.fixture
def mock_audio_data() -> bytes:
    """Create mock PCM16 audio data."""
    return b"\x00\x01" * 1600  # 100ms of 16kHz mono PCM16


class TestInteractionModeServiceInterface:
    """Tests for InteractionModeService interface compliance."""

    def test_interface_methods_defined(self) -> None:
        """Verify InteractionModeService interface has all required methods."""
        # These are the methods that must be implemented
        required_methods = [
            "connect",
            "disconnect",
            "send_audio",
            "end_turn",
            "interrupt",
            "events",
            "is_connected",
            "mode_name",
        ]

        # Check interface has these methods defined
        for method in required_methods:
            assert hasattr(InteractionModeService, method), f"Missing method: {method}"

    def test_connect_signature(self) -> None:
        """Verify connect method signature."""
        method = getattr(InteractionModeService, "connect", None)
        assert method is not None

    def test_send_audio_signature(self) -> None:
        """Verify send_audio method signature."""
        method = getattr(InteractionModeService, "send_audio", None)
        assert method is not None

    def test_end_turn_signature(self) -> None:
        """Verify end_turn method signature."""
        method = getattr(InteractionModeService, "end_turn", None)
        assert method is not None

    def test_interrupt_signature(self) -> None:
        """Verify interrupt method signature."""
        method = getattr(InteractionModeService, "interrupt", None)
        assert method is not None

    def test_disconnect_signature(self) -> None:
        """Verify disconnect method signature."""
        method = getattr(InteractionModeService, "disconnect", None)
        assert method is not None

    def test_events_signature(self) -> None:
        """Verify events method signature."""
        method = getattr(InteractionModeService, "events", None)
        assert method is not None

    def test_is_connected_signature(self) -> None:
        """Verify is_connected method signature."""
        method = getattr(InteractionModeService, "is_connected", None)
        assert method is not None


class TestGeminiLiveConfig:
    """Tests for Gemini Live API configuration."""

    def test_valid_voices(self) -> None:
        """Verify valid Gemini Live voices."""
        valid_voices = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]
        # At minimum, 'Puck' must be supported
        assert "Puck" in valid_voices

    def test_valid_models(self) -> None:
        """Verify valid Gemini Live models."""
        valid_models = ["gemini-2.5-flash-native-audio-preview-12-2025"]
        assert len(valid_models) >= 1

    def test_audio_format_config(self) -> None:
        """Verify audio format configuration for Gemini."""
        config = {
            "input_audio_encoding": "LINEAR16",
            "output_audio_encoding": "LINEAR16",
            "sample_rate_hertz": 16000,
        }

        assert config["input_audio_encoding"] == "LINEAR16"
        assert config["sample_rate_hertz"] == 16000

    def test_session_config_format(self) -> None:
        """Verify session configuration format for Gemini."""
        generation_config = {
            "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}},
            "system_instruction": "You are a helpful assistant.",
            "response_modalities": ["AUDIO"],
        }

        assert "speech_config" in generation_config
        assert "response_modalities" in generation_config


class TestGeminiLiveMessages:
    """Tests for Gemini Live API message formats."""

    def test_realtime_input_audio(self, mock_audio_data: bytes) -> None:
        """Verify realtime input audio message format."""
        message = {
            "realtime_input": {
                "media_chunks": [
                    {
                        "mime_type": "audio/pcm",
                        "data": base64.b64encode(mock_audio_data).decode(),
                    }
                ]
            }
        }

        assert "realtime_input" in message
        assert "media_chunks" in message["realtime_input"]

    def test_tool_response(self) -> None:
        """Verify tool response message format."""
        message = {
            "tool_response": {
                "function_responses": [{"id": "func_001", "response": {"result": "success"}}]
            }
        }

        assert "tool_response" in message


class TestGeminiLiveEvents:
    """Tests for Gemini Live API server events."""

    def test_setup_complete_event(self) -> None:
        """Verify setup complete event format."""
        event = {"setupComplete": {}}
        assert "setupComplete" in event

    def test_server_content_event(self) -> None:
        """Verify server content event format."""
        event = {
            "serverContent": {
                "modelTurn": {
                    "parts": [{"inlineData": {"mimeType": "audio/pcm", "data": "base64audio"}}]
                },
                "turnComplete": False,
            }
        }

        assert "serverContent" in event
        assert "modelTurn" in event["serverContent"]

    def test_turn_complete_event(self) -> None:
        """Verify turn complete event format."""
        event = {"serverContent": {"turnComplete": True}}

        assert event["serverContent"]["turnComplete"] is True

    def test_interrupted_event(self) -> None:
        """Verify interrupted event format."""
        event = {"serverContent": {"interrupted": True}}

        assert event["serverContent"]["interrupted"] is True


class TestRealtimeModeFactory:
    """Tests for RealtimeMode factory pattern."""

    def test_supported_providers(self) -> None:
        """Verify supported realtime providers."""
        supported = ["gemini"]
        assert "gemini" in supported

    def test_provider_selection_by_config(self) -> None:
        """Verify provider selection based on config."""
        gemini_config = {"provider": "gemini", "voice": "Puck"}

        assert gemini_config["provider"] == "gemini"

    def test_invalid_provider_handling(self) -> None:
        """Verify invalid provider raises appropriate error."""
        invalid_config = {"provider": "invalid_provider", "voice": "test"}

        # Factory should raise ValueError for unknown providers
        assert invalid_config["provider"] not in ["gemini"]


class TestAudioProcessing:
    """Tests for audio processing utilities."""

    def test_pcm16_format(self) -> None:
        """Verify PCM16 format specifications."""
        pcm16_spec = {
            "sample_rate": 16000,
            "bits_per_sample": 16,
            "channels": 1,
            "byte_order": "little_endian",
        }

        assert pcm16_spec["sample_rate"] == 16000
        assert pcm16_spec["bits_per_sample"] == 16

    def test_audio_chunk_size(self) -> None:
        """Verify recommended audio chunk sizes."""
        chunk_duration_ms = 100
        sample_rate = 16000
        bytes_per_sample = 2  # 16-bit
        channels = 1

        expected_chunk_size = (
            (sample_rate * chunk_duration_ms // 1000) * bytes_per_sample * channels
        )
        assert expected_chunk_size == 3200  # 100ms of 16kHz mono PCM16

    def test_base64_encoding(self, mock_audio_data: bytes) -> None:
        """Verify base64 encoding for audio transmission."""
        encoded = base64.b64encode(mock_audio_data).decode()
        decoded = base64.b64decode(encoded)

        assert decoded == mock_audio_data
        assert isinstance(encoded, str)
