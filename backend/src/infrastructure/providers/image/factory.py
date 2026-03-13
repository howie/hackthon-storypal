"""Image Provider Factory.

Creates image provider instances based on configuration.
"""

from __future__ import annotations

import os

from src.application.interfaces.image_provider import IImageProvider
from src.infrastructure.providers.image.gemini_imagen import GeminiImagenProvider


class ImageProviderFactory:
    """Factory for creating image provider instances."""

    @classmethod
    def create(cls, provider_name: str, **kwargs: object) -> IImageProvider:
        """Create an image provider by name."""
        if provider_name == "gemini-imagen":
            return cls._create_gemini_imagen(**kwargs)
        raise ValueError(f"Unknown image provider: {provider_name}")

    @classmethod
    def create_default(cls) -> IImageProvider:
        """Create the default image provider from environment variables."""
        return cls._create_gemini_imagen()

    @classmethod
    def _create_gemini_imagen(cls, **kwargs: object) -> GeminiImagenProvider:
        from src.config import get_settings

        api_key = str(kwargs.get("api_key", "")) or get_settings().gemini_api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for Gemini Imagen")
        model = str(kwargs.get("model", "")) or os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")
        return GeminiImagenProvider(api_key=api_key, model=model)
