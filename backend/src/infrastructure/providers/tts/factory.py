"""TTS Provider Factory.

T043: Factory for creating TTS providers with credential injection support.
T074: Extended to support audit logging for credential.used events.
"""

import os
import uuid
from dataclasses import dataclass
from typing import Any

from src.application.interfaces.tts_provider import ITTSProvider
from src.domain.repositories.provider_credential_repository import (
    IProviderCredentialRepository,
)


class ProviderNotSupportedError(Exception):
    """Raised when a provider is not supported."""

    pass


@dataclass
class ProviderCreationResult:
    """Result of provider creation, including credential metadata for audit logging."""

    provider: ITTSProvider
    used_user_credential: bool
    credential_id: uuid.UUID | None = None
    provider_name: str = ""


class TTSProviderFactory:
    """Factory for creating TTS provider instances.

    This factory supports:
    1. Creating providers with user credentials (BYOL model)
    2. Falling back to system-level credentials
    3. Caching provider instances
    """

    # Supported providers
    SUPPORTED_PROVIDERS = [
        "elevenlabs",
        "azure",
        "gcp",
        "gemini",
        "gemini-flash",
        "gemini-pro",
        "voai",
        "xgrok",
    ]

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names.

        Returns:
            List of supported provider identifiers
        """
        return cls.SUPPORTED_PROVIDERS.copy()

    @classmethod
    def is_supported(cls, provider_name: str) -> bool:
        """Check if a provider is supported.

        Args:
            provider_name: Provider identifier

        Returns:
            True if the provider is supported
        """
        return provider_name.lower() in cls.SUPPORTED_PROVIDERS

    @classmethod
    def _create_provider(
        cls, provider_name: str, api_key: str | None = None, **kwargs: Any
    ) -> ITTSProvider:
        """Internal method to create provider with given credentials.

        Args:
            provider_name: Name of the provider
            api_key: Optional API key override
            **kwargs: Additional provider-specific arguments

        Returns:
            ITTSProvider instance
        """
        provider_name = provider_name.lower()

        if provider_name == "elevenlabs":
            from src.infrastructure.providers.tts.elevenlabs_tts import (
                ElevenLabsTTSProvider,
            )

            return ElevenLabsTTSProvider(api_key=api_key or os.getenv("ELEVENLABS_API_KEY", ""))

        elif provider_name == "azure":
            from src.infrastructure.providers.tts.azure_tts import AzureTTSProvider

            return AzureTTSProvider(
                subscription_key=api_key or os.getenv("AZURE_SPEECH_KEY", ""),
                region=kwargs.get("region") or os.getenv("AZURE_SPEECH_REGION", "eastasia"),
            )

        elif provider_name == "gcp":
            from src.infrastructure.providers.tts.gcp_tts import GCPTTSProvider

            # GCP uses service account credentials, not API key
            return GCPTTSProvider(
                credentials_path=kwargs.get("credentials_path")
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            )

        elif provider_name in ("gemini", "gemini-flash", "gemini-pro"):
            from src.config import get_settings
            from src.infrastructure.providers.tts.gemini_tts import GeminiTTSProvider

            model_map = {
                "gemini-flash": "gemini-2.5-flash-preview-tts",
                "gemini-pro": "gemini-2.5-pro-preview-tts",
                "gemini": "gemini-2.5-pro-preview-tts",
            }
            fallback_map = {
                "gemini-flash": None,
                "gemini-pro": None,
                "gemini": "gemini-2.5-flash-preview-tts",
            }
            default_model = model_map[provider_name]
            default_fallback = fallback_map[provider_name]

            return GeminiTTSProvider(
                api_key=api_key or get_settings().gemini_api_key,
                model=kwargs.get("model") or default_model,
                fallback_model=kwargs.get("fallback_model", default_fallback),
            )

        elif provider_name == "voai":
            from src.infrastructure.providers.tts.voai_tts import VoAITTSProvider

            return VoAITTSProvider(
                api_key=api_key or os.getenv("VOAI_API_KEY", ""),
                api_endpoint=kwargs.get("api_endpoint")
                or os.getenv("VOAI_API_ENDPOINT", "connect.voai.ai"),
            )

        elif provider_name == "xgrok":
            from src.infrastructure.providers.tts.xgrok_tts import XGrokTTSProvider

            return XGrokTTSProvider(
                api_key=api_key or os.getenv("XAI_API_KEY", ""),
            )

        raise ProviderNotSupportedError(
            f"Provider '{provider_name}' is not supported. "
            f"Supported providers: {', '.join(cls.SUPPORTED_PROVIDERS)}"
        )

    @classmethod
    async def create(
        cls,
        provider_name: str,
        user_id: uuid.UUID | None = None,
        credential_repo: IProviderCredentialRepository | None = None,
        **kwargs: Any,
    ) -> ITTSProvider:
        """Create a TTS provider instance.

        If user_id and credential_repo are provided, attempts to use
        user credentials first. Falls back to system credentials.

        Args:
            provider_name: Name of the provider (e.g., 'elevenlabs', 'azure')
            user_id: Optional user ID for BYOL credential lookup
            credential_repo: Optional repository for looking up user credentials
            **kwargs: Additional provider-specific arguments

        Returns:
            ITTSProvider instance configured for the provider

        Raises:
            ProviderNotSupportedError: If the provider is not supported
        """
        result = await cls.create_with_metadata(
            provider_name=provider_name,
            user_id=user_id,
            credential_repo=credential_repo,
            **kwargs,
        )
        return result.provider

    @classmethod
    async def create_with_metadata(
        cls,
        provider_name: str,
        user_id: uuid.UUID | None = None,
        credential_repo: IProviderCredentialRepository | None = None,
        **kwargs: Any,
    ) -> ProviderCreationResult:
        """Create a TTS provider instance with credential metadata for audit logging.

        If user_id and credential_repo are provided, attempts to use
        user credentials first. Falls back to system credentials.

        Args:
            provider_name: Name of the provider (e.g., 'elevenlabs', 'azure')
            user_id: Optional user ID for BYOL credential lookup
            credential_repo: Optional repository for looking up user credentials
            **kwargs: Additional provider-specific arguments

        Returns:
            ProviderCreationResult with provider and credential metadata

        Raises:
            ProviderNotSupportedError: If the provider is not supported
        """
        provider_name = provider_name.lower()

        if not cls.is_supported(provider_name):
            raise ProviderNotSupportedError(
                f"Provider '{provider_name}' is not supported. "
                f"Supported providers: {', '.join(cls.SUPPORTED_PROVIDERS)}"
            )

        # Try to get user credential if user_id is provided
        # Normalize gemini-flash/gemini-pro to "gemini" for credential lookup
        credential_provider = "gemini" if provider_name.startswith("gemini") else provider_name
        api_key: str | None = None
        used_user_credential = False
        credential_id: uuid.UUID | None = None

        if user_id and credential_repo:
            user_credential = await credential_repo.get_by_user_and_provider(
                user_id, credential_provider
            )
            if user_credential and user_credential.is_valid:
                api_key = user_credential.api_key
                used_user_credential = True
                credential_id = user_credential.id

        provider = cls._create_provider(provider_name, api_key=api_key, **kwargs)

        return ProviderCreationResult(
            provider=provider,
            used_user_credential=used_user_credential,
            credential_id=credential_id,
            provider_name=provider_name,
        )

    @classmethod
    def create_with_key(cls, provider_name: str, api_key: str, **kwargs: Any) -> ITTSProvider:
        """Create a TTS provider instance with a specific API key.

        Args:
            provider_name: Name of the provider
            api_key: API key to use
            **kwargs: Additional provider-specific arguments

        Returns:
            ITTSProvider instance configured with the given key

        Raises:
            ProviderNotSupportedError: If the provider is not supported
        """
        if not cls.is_supported(provider_name):
            raise ProviderNotSupportedError(f"Provider '{provider_name}' is not supported")

        return cls._create_provider(provider_name, api_key=api_key, **kwargs)

    @classmethod
    def create_default(cls, provider_name: str, **kwargs: Any) -> ITTSProvider:
        """Create a TTS provider with default system credentials.

        Uses environment variables for credential lookup.

        Args:
            provider_name: Name of the provider
            **kwargs: Additional provider-specific arguments

        Returns:
            ITTSProvider instance with system credentials

        Raises:
            ProviderNotSupportedError: If the provider is not supported
        """
        if not cls.is_supported(provider_name):
            raise ProviderNotSupportedError(f"Provider '{provider_name}' is not supported")

        return cls._create_provider(provider_name, **kwargs)
