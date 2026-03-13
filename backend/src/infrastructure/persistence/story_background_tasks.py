"""Backward-compat shim for StoryPal background tasks.

The real implementation lives in application/tasks/story_tasks.py.
This module provides a concrete RepoFactory using AsyncSessionLocal so
existing callers (routes/story.py, tests) do not need immediate changes.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from src.application.interfaces.image_provider import IImageProvider
from src.application.interfaces.llm_provider import ILLMProvider
from src.application.interfaces.tts_provider import ITTSProvider
from src.application.tasks.story_tasks import (
    generate_images_background as _gen_images,
)
from src.application.tasks.story_tasks import (
    generate_story_background as _gen_story,
)
from src.application.tasks.story_tasks import (
    synthesize_story_background as _synth_story,
)
from src.domain.entities.story import StoryTemplate
from src.domain.repositories.story_repository import IStoryRepository
from src.infrastructure.persistence.database import AsyncSessionLocal
from src.infrastructure.persistence.story_repository_impl import StoryRepositoryImpl


@asynccontextmanager
async def _make_story_repo() -> AsyncGenerator[IStoryRepository, None]:
    async with AsyncSessionLocal() as db:
        yield StoryRepositoryImpl(db)


async def generate_story_background(
    session_id: str,
    template: StoryTemplate,
    language: str,
    llm: ILLMProvider,
    *,
    include_choice_points: bool = False,
) -> None:
    await _gen_story(
        session_id,
        template,
        language,
        llm,
        repo_factory=_make_story_repo,
        include_choice_points=include_choice_points,
    )


async def synthesize_story_background(
    session_id: str,
    char_voices: dict[str, str],
    tts: ITTSProvider,
    *,
    tts_provider_name: str = "gemini-pro",
) -> None:
    await _synth_story(
        session_id,
        char_voices,
        tts,
        tts_provider_name=tts_provider_name,
        repo_factory=_make_story_repo,
    )


async def generate_images_background(
    session_id: str,
    llm: ILLMProvider,
    image_provider: IImageProvider,
) -> None:
    await _gen_images(session_id, llm, image_provider, repo_factory=_make_story_repo)
