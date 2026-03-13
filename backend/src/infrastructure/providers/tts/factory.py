"""TTS Provider Factory — Gemini only for StoryPal."""

import os

from src.application.interfaces.tts_provider import ITTSProvider


class ProviderNotSupportedError(Exception):
    """Raised when a provider is not supported."""


class TTSProviderFactory:
    """Factory for creating TTS provider instances (Gemini only)."""

    SUPPORTED_PROVIDERS = ["gemini", "gemini-flash", "gemini-pro"]

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        return cls.SUPPORTED_PROVIDERS.copy()

    @classmethod
    def is_supported(cls, provider_name: str) -> bool:
        return provider_name.lower() in cls.SUPPORTED_PROVIDERS

    @classmethod
    def create_default(cls, provider_name: str) -> ITTSProvider:
        """Create a Gemini TTS provider with system credentials."""
        from src.config import get_settings
        from src.infrastructure.providers.tts.gemini_tts import GeminiTTSProvider

        provider_name = provider_name.lower()
        if not cls.is_supported(provider_name):
            raise ProviderNotSupportedError(
                f"Provider '{provider_name}' is not supported. "
                f"Supported: {', '.join(cls.SUPPORTED_PROVIDERS)}"
            )

        api_key = os.getenv("GEMINI_API_KEY") or get_settings().gemini_api_key
        model_map = {
            "gemini-flash": "gemini-2.5-flash-preview-tts",
            "gemini-pro": "gemini-2.5-pro-preview-tts",
            "gemini": "gemini-2.5-pro-preview-tts",
        }

        return GeminiTTSProvider(
            api_key=api_key,
            model=model_map[provider_name],
            fallback_model=None,
        )
