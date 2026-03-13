"""Gemini Imagen 4 image generation provider.

Uses the Imagen 4 `:predict` endpoint via Google AI Generative Language API.
"""

from __future__ import annotations

import base64
import logging
import time

import httpx

from src.application.interfaces.image_provider import (
    IImageProvider,
    ImageGenerationResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "imagen-4.0-generate-001"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiImagenProvider(IImageProvider):
    """Imagen 4 provider using the Google AI Generative Language API."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def name(self) -> str:
        return "gemini-imagen"

    async def generate_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
    ) -> ImageGenerationResult:
        """Generate an image using Imagen 4 :predict endpoint."""
        url = f"{_BASE_URL}/{self._model}:predict"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": aspect_ratio,
                "personGeneration": "allow_adult",
            },
        }

        start = time.monotonic()
        response = await self._client.post(
            url,
            json=payload,
            params={"key": self._api_key},
        )

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code == 429:
            raise QuotaExceededError(f"Imagen API quota exceeded (429): {response.text}")

        if response.status_code != 200:
            # Try to extract structured error message from JSON response
            error_detail = response.text[:200]
            try:
                err_body = response.json()
                err_obj = err_body.get("error", {})
                if isinstance(err_obj, dict) and err_obj.get("message"):
                    error_detail = (
                        f"[{err_obj.get('code', response.status_code)}] {err_obj['message']}"
                    )
            except Exception:
                pass
            logger.error(
                "Imagen API error: status=%d body=%s",
                response.status_code,
                response.text[:500],
            )
            raise ImageProviderError(f"Imagen API returned {response.status_code}: {error_detail}")

        data = response.json()
        predictions = data.get("predictions", [])
        if not predictions:
            logger.error("Imagen API returned no predictions. keys: %s", list(data.keys()))
            raise ImageProviderError("Imagen API returned empty predictions")

        pred = predictions[0]
        image_b64 = pred.get("bytesBase64Encoded", "")
        if not image_b64:
            raise ImageProviderError("Imagen API returned prediction without image data")

        image_bytes = base64.b64decode(image_b64)
        mime_type = pred.get("mimeType", "image/png")

        return ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            provider="gemini-imagen",
            model=self._model,
            latency_ms=latency_ms,
        )

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()


class ImageProviderError(Exception):
    """Error from image provider."""


class QuotaExceededError(ImageProviderError):
    """Imagen API quota exceeded (429)."""
