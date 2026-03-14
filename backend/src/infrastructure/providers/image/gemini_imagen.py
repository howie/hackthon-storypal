"""Gemini Imagen 4 image generation provider using Google GenAI SDK.

Uses the Imagen 4 model via Google GenAI SDK for image generation.
"""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import types

from src.application.interfaces.image_provider import (
    IImageProvider,
    ImageGenerationResult,
)
from src.domain.errors import QuotaExceededError

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "imagen-4.0-generate-001"


class GeminiImagenProvider(IImageProvider):
    """Imagen 4 provider using the Google GenAI SDK."""

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
        self._client = genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        return "gemini-imagen"

    async def generate_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
    ) -> ImageGenerationResult:
        """Generate an image using Imagen 4 via GenAI SDK."""
        start = time.monotonic()

        try:
            response = await self._client.aio.models.generate_images(
                model=self._model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    person_generation="allow_adult",
                ),
            )
        except Exception as e:
            error_message = str(e)
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                raise QuotaExceededError(
                    provider="gemini-imagen",
                    original_error=error_message,
                ) from e
            logger.error("Imagen API error: %s", error_message)
            raise ImageProviderError(f"Imagen API error: {error_message}") from e

        latency_ms = int((time.monotonic() - start) * 1000)

        if not response.generated_images:
            logger.error("Imagen API returned no images")
            raise ImageProviderError("Imagen API returned empty predictions")

        generated = response.generated_images[0]
        image_bytes = generated.image.image_bytes
        if not image_bytes:
            raise ImageProviderError("Imagen API returned prediction without image data")

        mime_type = getattr(generated.image, "mime_type", "image/png") or "image/png"

        return ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            provider="gemini-imagen",
            model=self._model,
            latency_ms=latency_ms,
        )

    async def close(self) -> None:
        """Close the provider (no-op for GenAI SDK)."""
        pass


class ImageProviderError(Exception):
    """Error from image provider."""
