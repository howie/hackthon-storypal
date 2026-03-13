"""Unit tests for GeminiImagenProvider and ImageProviderFactory.

Feature: 019-story-pixel-images (T017)
Tests:
  - Request format sent to Imagen 4 :predict endpoint
  - Successful response parsing (base64 image bytes, mime type, latency)
  - 429 quota exceeded → raises QuotaExceededError
  - Non-200 error → raises ImageProviderError
  - Empty predictions → raises ImageProviderError
  - Missing image data in prediction → raises ImageProviderError
  - Factory env var fallback (GEMINI_API_KEY)
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock

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


def _make_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    """Create a mock httpx Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    return resp


# =============================================================================
# Successful generation
# =============================================================================


@pytest.mark.asyncio
async def test_generate_image_success(provider: GeminiImagenProvider) -> None:
    """Verify correct request payload and response parsing."""
    image_bytes = b"\x89PNG\r\n\x1a\nfake-image-data"
    b64 = base64.b64encode(image_bytes).decode()

    mock_resp = _make_response(
        json_data={
            "predictions": [
                {
                    "bytesBase64Encoded": b64,
                    "mimeType": "image/png",
                }
            ]
        }
    )

    provider._client = AsyncMock()
    provider._client.post = AsyncMock(return_value=mock_resp)

    result = await provider.generate_image("pixel art style, a cute fox", aspect_ratio="1:1")

    # Verify request format
    call_args = provider._client.post.call_args
    assert call_args.args[0].endswith(":predict")
    payload = call_args.kwargs["json"]
    assert payload["instances"][0]["prompt"] == "pixel art style, a cute fox"
    assert payload["parameters"]["aspectRatio"] == "1:1"
    assert payload["parameters"]["sampleCount"] == 1

    # Verify params contain API key
    assert call_args.kwargs["params"] == {"key": "test-key"}

    # Verify result
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
    """429 response raises QuotaExceededError."""
    mock_resp = _make_response(status_code=429, text="quota exceeded")
    provider._client = AsyncMock()
    provider._client.post = AsyncMock(return_value=mock_resp)

    with pytest.raises(QuotaExceededError, match="429"):
        await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_server_error(provider: GeminiImagenProvider) -> None:
    """Non-200 response raises ImageProviderError."""
    mock_resp = _make_response(status_code=500, text="Internal Server Error")
    provider._client = AsyncMock()
    provider._client.post = AsyncMock(return_value=mock_resp)

    with pytest.raises(ImageProviderError, match="500"):
        await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_structured_error(provider: GeminiImagenProvider) -> None:
    """Structured JSON error body is parsed into exception message."""
    mock_resp = _make_response(
        status_code=400,
        json_data={"error": {"code": 400, "message": "Invalid prompt"}},
        text='{"error":{"code":400,"message":"Invalid prompt"}}',
    )
    provider._client = AsyncMock()
    provider._client.post = AsyncMock(return_value=mock_resp)

    with pytest.raises(ImageProviderError, match=r"\[400\] Invalid prompt"):
        await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_empty_predictions(provider: GeminiImagenProvider) -> None:
    """Empty predictions list raises ImageProviderError."""
    mock_resp = _make_response(json_data={"predictions": []})
    provider._client = AsyncMock()
    provider._client.post = AsyncMock(return_value=mock_resp)

    with pytest.raises(ImageProviderError, match="empty predictions"):
        await provider.generate_image("test prompt")


@pytest.mark.asyncio
async def test_generate_image_no_image_data(provider: GeminiImagenProvider) -> None:
    """Prediction without image bytes raises ImageProviderError."""
    mock_resp = _make_response(json_data={"predictions": [{"mimeType": "image/png"}]})
    provider._client = AsyncMock()
    provider._client.post = AsyncMock(return_value=mock_resp)

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
    """close() calls aclose on httpx client."""
    provider._client = AsyncMock()
    provider._client.aclose = AsyncMock()

    await provider.close()

    provider._client.aclose.assert_awaited_once()


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
    # Use setenv("", "") to override .env file values; delenv alone does not
    # prevent pydantic-settings from reading the .env file.
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        ImageProviderFactory.create_default()
