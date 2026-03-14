"""Unit tests for GeminiImagenProvider and ImageProviderFactory.

Feature: 019-story-pixel-images (T017)
Tests:
  - Successful response parsing (image bytes, mime type, latency)
  - Exception handling (quota exceeded, general errors)
  - Empty predictions → raises ImageProviderError
  - Missing image data in prediction → raises ImageProviderError
  - Factory env var fallback (GEMINI_API_KEY)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.providers.image.factory import ImageProviderFactory
from src.infrastructure.providers.image.gemini_imagen import (
    GeminiImagenProvider,
    ImageProviderError,
    QuotaExceededError,
)


@pytest.fixture
def provider() -> GeminiImagenProvider:
    return GeminiImagenProvider(api_key="test-key", model="imagen-4.0-generate-001")


def _make_sdk_response(
    image_bytes: bytes = b"\x89PNG\r\n\x1a\nfake-image-data",
    mime_type: str = "image/png",
) -> MagicMock:
    """Create a mock GenAI SDK generate_images response."""
    mock_image = MagicMock()
    mock_image.image_bytes = image_bytes
    mock_image.mime_type = mime_type

    mock_generated = MagicMock()
    mock_generated.image = mock_image

    mock_response = MagicMock()
    mock_response.generated_images = [mock_generated]
    return mock_response


def _make_empty_sdk_response() -> MagicMock:
    """Create a mock GenAI SDK response with no images."""
    mock_response = MagicMock()
    mock_response.generated_images = []
    return mock_response


def _make_no_bytes_sdk_response() -> MagicMock:
    """Create a mock GenAI SDK response where image has no bytes."""
    mock_image = MagicMock()
    mock_image.image_bytes = None
    mock_image.mime_type = "image/png"

    mock_generated = MagicMock()
    mock_generated.image = mock_image

    mock_response = MagicMock()
    mock_response.generated_images = [mock_generated]
    return mock_response


# =============================================================================
# Successful generation
# =============================================================================


@pytest.mark.asyncio
async def test_generate_image_success(provider: GeminiImagenProvider) -> None:
    """Verify correct response parsing from GenAI SDK."""
    image_bytes = b"\x89PNG\r\n\x1a\nfake-image-data"
    mock_resp = _make_sdk_response(image_bytes=image_bytes, mime_type="image/png")

    mock_generate = AsyncMock(return_value=mock_resp)
    with patch.object(provider._client.aio.models, "generate_images", mock_generate):
        result = await provider.generate_image("pixel art style, a cute fox", aspect_ratio="1:1")

    assert result.image_bytes == image_bytes
    assert result.mime_type == "image/png"
    assert result.provider == "gemini-imagen"
    assert result.model == "imagen-4.0-generate-001"
    assert result.latency_ms >= 0


# =============================================================================
# Error cases
# =============================================================================


@pytest.mark.asyncio
async def test_generate_image_quota_exceeded(provider: GeminiImagenProvider) -> None:
    """429 exception raises QuotaExceededError."""
    mock_generate = AsyncMock(side_effect=Exception("429 RESOURCE_EXHAUSTED: quota exceeded"))
    with patch.object(provider._client.aio.models, "generate_images", mock_generate):
        with pytest.raises(QuotaExceededError, match="429"):
            await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_server_error(provider: GeminiImagenProvider) -> None:
    """Non-quota exception raises ImageProviderError."""
    mock_generate = AsyncMock(side_effect=Exception("500 Internal Server Error"))
    with patch.object(provider._client.aio.models, "generate_images", mock_generate):
        with pytest.raises(ImageProviderError, match="500"):
            await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_empty_predictions(provider: GeminiImagenProvider) -> None:
    """Empty generated_images raises ImageProviderError."""
    mock_resp = _make_empty_sdk_response()
    mock_generate = AsyncMock(return_value=mock_resp)
    with patch.object(provider._client.aio.models, "generate_images", mock_generate):
        with pytest.raises(ImageProviderError, match="empty predictions"):
            await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_no_image_data(provider: GeminiImagenProvider) -> None:
    """Generated image without bytes raises ImageProviderError."""
    mock_resp = _make_no_bytes_sdk_response()
    mock_generate = AsyncMock(return_value=mock_resp)
    with patch.object(provider._client.aio.models, "generate_images", mock_generate):
        with pytest.raises(ImageProviderError, match="without image data"):
            await provider.generate_image("test prompt")


# =============================================================================
# Provider identity
# =============================================================================


def test_provider_name(provider: GeminiImagenProvider) -> None:
    """Provider name is 'gemini-imagen'."""
    assert provider.name == "gemini-imagen"


@pytest.mark.asyncio
async def test_close(provider: GeminiImagenProvider) -> None:
    """close() is a no-op for GenAI SDK."""
    await provider.close()  # Should not raise


# =============================================================================
# Factory env var fallback
# =============================================================================


def test_factory_gemini_api_key_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Factory resolves canonical GEMINI_API_KEY."""
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-123")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")

    p = ImageProviderFactory.create_default()
    assert isinstance(p, GeminiImagenProvider)
    assert p._api_key == "gemini-key-123"


def test_factory_gemini_api_key_preferred(monkeypatch: pytest.MonkeyPatch) -> None:
    """GEMINI_API_KEY takes priority over GOOGLE_AI_API_KEY (canonical key first)."""
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-123")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "google-key-456")
    monkeypatch.setenv("GOOGLE_API_KEY", "")

    p = ImageProviderFactory.create_default()
    assert isinstance(p, GeminiImagenProvider)
    assert p._api_key == "gemini-key-123"


def test_factory_no_key_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Factory raises ValueError when no API key is set."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        ImageProviderFactory.create_default()
