"""FastAPI Dependencies - Dependency Injection Container.

Simplified for StoryPal: only Gemini providers + local/GCS storage.
"""

import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.llm_provider import ILLMProvider
from src.application.interfaces.storage_service import IStorageService
from src.application.interfaces.tts_provider import ITTSProvider
from src.config import get_settings
from src.domain.repositories.story_repository import IStoryRepository
from src.infrastructure.persistence.database import get_db_session
from src.infrastructure.persistence.story_repository_impl import StoryRepositoryImpl
from src.infrastructure.storage import LocalStorageService


class Container:
    """Dependency Injection Container."""

    _instance: "Container | None" = None
    _tts_providers: dict[str, ITTSProvider] | None = None
    _llm_providers: dict[str, ILLMProvider] | None = None
    _storage_service: IStorageService | None = None

    @classmethod
    def get_instance(cls) -> "Container":
        """Get singleton container instance."""
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    def get_tts_providers(self) -> dict[str, ITTSProvider]:
        """Get TTS providers (lazy initialization)."""
        if self._tts_providers is None:
            self._tts_providers = self._create_tts_providers()
        return self._tts_providers

    def get_llm_providers(self) -> dict[str, ILLMProvider]:
        """Get LLM providers (lazy initialization)."""
        if self._llm_providers is None:
            self._llm_providers = self._create_llm_providers()
        return self._llm_providers

    def get_storage_service(self) -> IStorageService:
        """Get storage service."""
        if self._storage_service is None:
            self._storage_service = self._create_storage_service()
        return self._storage_service

    def _create_tts_providers(self) -> dict[str, ITTSProvider]:
        """Create TTS provider instances — Gemini only."""
        providers: dict[str, ITTSProvider] = {}

        gemini_api_key = get_settings().gemini_api_key
        if gemini_api_key:
            try:
                from src.infrastructure.providers.tts import GeminiTTSProvider

                providers["gemini-flash"] = GeminiTTSProvider(
                    api_key=gemini_api_key,
                    model="gemini-2.5-flash-preview-tts",
                    fallback_model=None,
                )
                providers["gemini-pro"] = GeminiTTSProvider(
                    api_key=gemini_api_key,
                    model="gemini-2.5-pro-preview-tts",
                    fallback_model=None,
                )
            except Exception as e:
                print(f"Failed to initialize Gemini TTS: {e}")

        return providers

    def _create_llm_providers(self) -> dict[str, ILLMProvider]:
        """Create LLM provider instances — Gemini only."""
        providers: dict[str, ILLMProvider] = {}

        gemini_key = get_settings().gemini_api_key
        if gemini_key:
            try:
                from src.infrastructure.providers.llm import GeminiLLMProvider

                providers["gemini"] = GeminiLLMProvider(
                    api_key=gemini_key,
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                )
            except Exception as e:
                print(f"Failed to initialize Gemini LLM: {e}")

        return providers

    def _create_storage_service(self) -> IStorageService:
        """Create storage service based on configuration."""
        storage_type = os.getenv("STORAGE_TYPE", "local")

        if storage_type == "gcs":
            from src.infrastructure.storage.gcs_storage import GCSStorageService

            return GCSStorageService(
                bucket_name=os.getenv("AUDIO_BUCKET", "storypal-audio"),
            )
        else:
            return LocalStorageService(
                base_path=os.getenv("LOCAL_STORAGE_PATH", "./storage"),
            )


# FastAPI dependency functions


def get_container() -> Container:
    """Get the DI container."""
    return Container.get_instance()


def get_tts_providers() -> dict[str, ITTSProvider]:
    """FastAPI dependency for TTS providers."""
    return get_container().get_tts_providers()


def get_llm_providers() -> dict[str, ILLMProvider]:
    """FastAPI dependency for LLM providers."""
    return get_container().get_llm_providers()


def get_storage_service() -> IStorageService:
    """FastAPI dependency for storage service."""
    return get_container().get_storage_service()


def get_story_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IStoryRepository:
    """FastAPI dependency for story repository."""
    return StoryRepositoryImpl(session)
