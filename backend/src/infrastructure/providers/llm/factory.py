"""LLM Provider Factory.

Feature: 004-interaction-module
T043: Factory for creating LLM providers for Cascade mode.
"""

from typing import Any

from src.application.interfaces.llm_provider import ILLMProvider
from src.infrastructure.providers.llm.gemini_llm import GeminiLLMProvider


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    PROVIDER_INFO = {
        "gemini": {
            "name": "gemini",
            "display_name": "Google Gemini",
            "default_model": "gemini-2.5-flash",
            "supports_streaming": True,
            "max_tokens": 8192,
        },
    }

    @classmethod
    def create(cls, provider_name: str, credentials: dict[str, Any]) -> ILLMProvider:
        """Create an LLM provider instance.

        Args:
            provider_name: Name of the provider
            credentials: Provider-specific credentials

        Returns:
            Configured LLM provider instance

        Raises:
            ValueError: If provider name is unknown or credentials are invalid
        """
        provider_name = provider_name.lower()

        if provider_name == "gemini":
            return cls._create_gemini(credentials)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

    @classmethod
    def create_default(cls, provider_name: str) -> ILLMProvider:
        """Create an LLM provider with default system credentials from env vars.

        Args:
            provider_name: Name of the provider

        Returns:
            Configured LLM provider instance
        """
        provider_name = provider_name.lower()

        if provider_name == "gemini":
            from src.config import get_settings

            api_key = get_settings().gemini_api_key
            return GeminiLLMProvider(api_key=api_key)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

    @classmethod
    def _create_gemini(cls, credentials: dict[str, Any]) -> GeminiLLMProvider:
        from src.config import get_settings

        api_key = credentials.get("api_key") or get_settings().gemini_api_key
        model = credentials.get("model", "gemini-2.5-flash")
        if not api_key:
            raise ValueError("Gemini LLM requires 'api_key'")
        return GeminiLLMProvider(api_key=api_key, model=model)

    @classmethod
    def get_provider_info(cls, provider_name: str) -> dict[str, Any]:
        """Get provider metadata."""
        provider_name = provider_name.lower()
        if provider_name not in cls.PROVIDER_INFO:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
        return cls.PROVIDER_INFO[provider_name]

    @classmethod
    def list_providers(cls) -> list[dict[str, Any]]:
        """List all available providers with metadata."""
        return list(cls.PROVIDER_INFO.values())

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names."""
        return list(cls.PROVIDER_INFO.keys())
