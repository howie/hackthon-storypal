"""StoryPal background task functions (Application Service layer).

Feature: 017-storypal (Clean Architecture Sprint 2)
Background tasks for story generation, TTS synthesis, and image generation.

Coordinates domain services + external providers + storage + DB.
Moved from infrastructure/persistence/ to application/tasks/ (Phase 2 refactor).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, TypeAlias

from src.application.interfaces.image_provider import IImageProvider
from src.application.interfaces.llm_provider import ILLMProvider, LLMResponse
from src.application.interfaces.tts_provider import ITTSProvider
from src.domain.entities.audio import AudioFormat
from src.domain.entities.story import StoryTemplate
from src.domain.entities.tts import TTSRequest
from src.domain.errors import QuotaExceededError
from src.domain.repositories.story_repository import IStoryRepository
from src.domain.services.story.cost_calculator import (
    estimate_image_cost,
    estimate_llm_cost,
    estimate_tts_cost,
)
from src.domain.services.story.engine import StoryEngine
from src.domain.services.story.prompts import PIXEL_ART_STYLE_PREFIX
from src.infrastructure.providers.image.gemini_imagen import (
    QuotaExceededError as ImageQuotaError,
)
from src.infrastructure.storage.factory import create_storage_service

logger = logging.getLogger(__name__)

RepoFactory: TypeAlias = Callable[[], AbstractAsyncContextManager[IStoryRepository]]

# Voice pool for automatic assignment (round-robin) when no template provides voices
_VOICE_POOL = (
    "Callirrhoe",
    "Despina",
    "Autonoe",
    "Kore",
    "Laomedeia",
    "Leda",
    "Sulafat",
    "Puck",
    "Charon",
    "Fenrir",
    "Aoede",
)

# Default voice for single-role narration; must exist in _VOICE_POOL
_DEFAULT_VOICE = "Kore"


async def _mark_session_failed(
    session_id: str,
    status_key: str,
    error_key: str,
    message: str,
    repo_factory: RepoFactory,
) -> None:
    """Update session status to 'failed' in a separate DB session.

    Best-effort fallback called from background task exception handlers.
    Swallows its own exceptions to avoid masking the original error.
    """
    try:
        async with repo_factory() as repo:
            await repo.update_session_state(
                uuid.UUID(session_id),
                {status_key: "failed", error_key: message},
            )
    except Exception:
        logger.exception("Failed to update error state for session %s", session_id)


async def _record_cost_event(
    session_id: str,
    event_type: str,
    response: LLMResponse,
    *,
    repo_factory: RepoFactory,
    characters_count: int = 0,
) -> None:
    """Best-effort persist a cost event. Failures are logged, never raised."""
    try:
        if event_type == "tts":
            cost = estimate_tts_cost(response.provider, characters_count)
        elif event_type == "image":
            cost = estimate_image_cost(response.provider)
        else:
            cost = estimate_llm_cost(response.model, response.input_tokens, response.output_tokens)
        async with repo_factory() as repo:
            await repo.create_cost_event(
                {
                    "id": uuid.uuid4(),
                    "session_id": uuid.UUID(session_id),
                    "event_type": event_type,
                    "provider": response.provider,
                    "model": response.model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "characters_count": characters_count,
                    "latency_ms": response.latency_ms,
                    "cost_estimate": cost,
                }
            )
    except Exception:
        logger.warning("Failed to record cost event for session %s", session_id, exc_info=True)


async def _record_tts_cost_event(
    session_id: str,
    provider: str,
    characters: int,
    latency_ms: int,
    *,
    repo_factory: RepoFactory,
) -> None:
    """Best-effort persist a TTS cost event."""
    try:
        cost = estimate_tts_cost(provider, characters)
        async with repo_factory() as repo:
            await repo.create_cost_event(
                {
                    "id": uuid.uuid4(),
                    "session_id": uuid.UUID(session_id),
                    "event_type": "tts",
                    "provider": provider,
                    "model": "",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "characters_count": characters,
                    "latency_ms": latency_ms,
                    "cost_estimate": cost,
                }
            )
    except Exception:
        logger.warning("Failed to record TTS cost event for session %s", session_id, exc_info=True)


async def _record_image_cost_event(
    session_id: str,
    provider: str,
    latency_ms: int,
    *,
    repo_factory: RepoFactory,
) -> None:
    """Best-effort persist an image generation cost event."""
    try:
        cost = estimate_image_cost(provider)
        async with repo_factory() as repo:
            await repo.create_cost_event(
                {
                    "id": uuid.uuid4(),
                    "session_id": uuid.UUID(session_id),
                    "event_type": "image",
                    "provider": provider,
                    "model": "",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "characters_count": 0,
                    "latency_ms": latency_ms,
                    "cost_estimate": cost,
                }
            )
    except Exception:
        logger.warning(
            "Failed to record image cost event for session %s", session_id, exc_info=True
        )


@dataclass
class _ImageResult:
    turn_number: int
    success: bool
    quota_exceeded: bool = False


async def generate_story_background(
    session_id: str,
    template: StoryTemplate,
    language: str,
    llm: ILLMProvider,
    *,
    repo_factory: RepoFactory,
    include_choice_points: bool = False,
) -> None:
    """Background task: generate story and save turns to DB.

    Replaces _generate_story_background from presentation/api/routes/story.py.
    """
    try:

        async def _on_cost(event_type: str, resp: LLMResponse) -> None:
            await _record_cost_event(session_id, event_type, resp, repo_factory=repo_factory)

        engine = StoryEngine(llm, cost_callback=_on_cost)
        segments = await engine.generate_complete_story(
            template, language, include_choice_points=include_choice_points
        )

        turns_data = [
            {
                "id": uuid.uuid4(),
                "turn_number": i,
                "turn_type": seg.type.value,
                "character_name": seg.character_name,
                "content": seg.content,
                "bgm_scene": seg.scene,
                "choice_options": seg.choice_options,
            }
            for i, seg in enumerate(segments, start=1)
        ]

        async with repo_factory() as repo:
            session_uuid = uuid.UUID(session_id)
            db_session = await repo.get_session_with_turns(session_uuid)
            if not db_session:
                logger.error("Session %s not found in background generate task", session_id)
                return

            # Clean up GCS audio/image files from old turns before deleting DB records
            storage_paths: list[str] = []
            for t in db_session.turns or []:
                if t.audio_path:
                    storage_paths.append(t.audio_path)
                if getattr(t, "image_path", None):
                    storage_paths.append(t.image_path)
            if storage_paths:
                storage = create_storage_service()
                results = await asyncio.gather(
                    *(storage.delete(path) for path in storage_paths),
                    return_exceptions=True,
                )
                for path, result in zip(storage_paths, results, strict=True):
                    if isinstance(result, Exception):
                        logger.warning("Failed to delete old storage file: %s", path)

            # Delegate turns replace + status update to repository
            await repo.create_turns(session_uuid, turns_data)
            logger.info("Background story generation completed for session %s", session_id)

    except Exception:
        logger.exception("Background story generation failed for session %s", session_id)
        await _mark_session_failed(
            session_id,
            "generation_status",
            "generation_error",
            "Story generation failed",
            repo_factory,
        )


async def _auto_generate_qa(
    session_id: str,
    llm: ILLMProvider,
    repo_factory: RepoFactory,
) -> None:
    """Auto-generate Q&A content after story generation completes (non-fatal).

    Opens a fresh DB session (generation session already committed).
    Failures are logged as warnings and do not affect generation_status.
    """
    from src.domain.entities.story import ChildConfig as DomainChildConfig
    from src.domain.entities.story import StorySession, StoryTurn, StoryTurnType
    from src.domain.services.story.content_generator import StoryContentGenerator

    try:
        async with repo_factory() as repo:
            session_uuid = uuid.UUID(session_id)
            db_session = await repo.get_session_with_turns(session_uuid)
            if not db_session:
                logger.warning("_auto_generate_qa: session %s not found", session_id)
                return

            # Inline domain conversion (avoids cross-layer import from presentation)
            child_data = db_session.child_config or {}
            child = DomainChildConfig(
                age=child_data.get("age", 4),
                learning_goals=child_data.get("learning_goals", ""),
                selected_values=child_data.get("selected_values", []),
                selected_emotions=child_data.get("selected_emotions", []),
                favorite_character=child_data.get("favorite_character", ""),
                child_name=child_data.get("child_name", "小朋友"),
                voice_id=child_data.get("voice_id"),
            )
            turns = []
            for t in sorted(db_session.turns or [], key=lambda x: x.turn_number):
                try:
                    turn_type = StoryTurnType(t.turn_type)
                except ValueError:
                    turn_type = StoryTurnType.NARRATION
                turns.append(
                    StoryTurn(
                        session_id=db_session.id,
                        turn_number=t.turn_number,
                        turn_type=turn_type,
                        content=t.content,
                        id=t.id,
                        character_name=t.character_name,
                        created_at=t.created_at,
                    )
                )
            domain_session = StorySession(
                id=db_session.id,
                title=db_session.title,
                language=db_session.language,
                user_id=str(db_session.user_id),
                template_id=db_session.template_id,
                story_state=db_session.story_state or {},
                child_config=child,
                turns=turns,
                started_at=db_session.started_at,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at,
            )

            generated = await StoryContentGenerator(llm).generate_qa(domain_session)
            await repo.create_generated_content(
                {
                    "id": uuid.uuid4(),
                    "session_id": session_uuid,
                    "content_type": generated.content_type.value,
                    "content_data": generated.content_data,
                }
            )
            logger.info("Auto-generated Q&A for session %s", session_id)
    except Exception:
        logger.warning(
            "Auto Q&A generation failed for session %s (non-fatal)",
            session_id,
            exc_info=True,
        )


def _auto_assign_voices(
    turns: list[Any],
    default_voice: str,
) -> dict[str, str]:
    """Auto-assign voices from pool to unique character names (round-robin).

    When no template provides character→voice mapping, collect unique character
    names from turns and assign voices from ``_VOICE_POOL`` in round-robin order.
    """
    char_names = list(dict.fromkeys(t.character_name for t in turns if t.character_name))
    if not char_names:
        return {}

    result = {
        name: _VOICE_POOL[i % len(_VOICE_POOL)] if _VOICE_POOL else default_voice
        for i, name in enumerate(char_names)
    }
    logger.info("Auto-assigned voices: %s", result)
    return result


async def _update_synthesis_progress(
    session_id: str,
    completed: int,
    total: int,
    *,
    repo_factory: RepoFactory,
) -> None:
    """Update synthesis progress in story_state JSONB (separate session)."""
    async with repo_factory() as repo:
        await repo.update_session_state(
            uuid.UUID(session_id),
            {"synthesis_progress": {"completed": completed, "total": total}},
        )


async def synthesize_story_background(
    session_id: str,
    char_voices: dict[str, str],
    tts: ITTSProvider,
    *,
    tts_provider_name: str = "gemini-pro",
    repo_factory: RepoFactory,
) -> None:
    """Background task: synthesize TTS for all turns with progress updates.

    Replaces _synthesize_story_background from presentation/api/routes/story.py.
    """
    try:
        async with repo_factory() as repo:
            session_uuid = uuid.UUID(session_id)
            db_session = await repo.get_session_with_turns(session_uuid)
            if not db_session:
                logger.error("Session %s not found in background synthesize task", session_id)
                return

            turns_to_synth = sorted(db_session.turns or [], key=lambda t: t.turn_number)
            total = len(turns_to_synth)
            default_voice = _DEFAULT_VOICE

            # Voice mode: single_role uses one narrator voice for all turns
            story_state = db_session.story_state or {}
            voice_mode = story_state.get("voice_mode", "multi_role")
            storage = create_storage_service()

            # Auto-assign voices from pool when char_voices is empty (no template)
            if voice_mode == "multi_role" and not char_voices:
                char_voices = _auto_assign_voices(turns_to_synth, default_voice)

            logger.info(
                "Synthesis storage backend: %s for session %s (voice_mode=%s)",
                type(storage).__name__,
                session_id,
                voice_mode,
            )
            logger.debug("char_voices for session %s: %s", session_id, char_voices)

            completed = 0
            failed_count = 0
            quota_exceeded = False
            for turn in turns_to_synth:
                # Skip if already synthesized
                if turn.audio_path:
                    completed += 1
                    await _update_synthesis_progress(
                        session_id, completed, total, repo_factory=repo_factory
                    )
                    continue

                if voice_mode == "single_role":
                    voice_id = default_voice
                else:
                    voice_id = char_voices.get(turn.character_name or "", default_voice)
                try:
                    req = TTSRequest(
                        text=turn.content,
                        voice_id=voice_id,
                        provider=tts_provider_name,
                        language="zh-TW",
                        output_format=AudioFormat.MP3,
                    )
                    tts_result = await tts.synthesize(req)
                    await _record_tts_cost_event(
                        session_id,
                        "gemini",
                        len(turn.content),
                        tts_result.latency_ms,
                        repo_factory=repo_factory,
                    )
                    storage_key = f"story/{session_id}/{turn.turn_number}.mp3"
                    await storage.upload(
                        key=storage_key,
                        data=tts_result.audio.data,
                        content_type="audio/mpeg",
                    )
                    # Direct ORM attribute update (valid in infra layer)
                    turn.audio_path = storage_key
                except QuotaExceededError:
                    quota_exceeded = True
                    failed_count += 1
                    logger.warning(
                        "TTS quota exceeded for turn %d in session %s",
                        turn.turn_number,
                        session_id,
                        exc_info=True,
                    )
                    break  # Subsequent turns will also fail — stop wasting API calls
                except Exception:
                    failed_count += 1
                    logger.warning(
                        "TTS synthesis failed for turn %d in session %s",
                        turn.turn_number,
                        session_id,
                        exc_info=True,
                    )

                completed += 1
                await _update_synthesis_progress(
                    session_id, completed, total, repo_factory=repo_factory
                )

            # Verify actual audio output instead of trusting absence-of-exception
            synth_succeeded = sum(1 for t in turns_to_synth if t.audio_path)

            # Determine final status
            if quota_exceeded:
                synth_status = "failed"
                synth_error: str | None = "quota_exceeded"
            elif synth_succeeded == 0 and total > 0:
                synth_status = "failed"
                synth_error = "語音合成失敗，請稍後重試"
            elif synth_succeeded < total:
                synth_status = "completed"
                synth_error = f"部分音段合成失敗 ({synth_succeeded}/{total})"
            else:
                synth_status = "completed"
                synth_error = None

            # Commit audio_path mutations on turn ORM objects + final session status
            await repo.update_session_state(
                session_uuid,
                {
                    "synthesis_status": synth_status,
                    "synthesis_error": synth_error,
                    # synthesis_progress in JSONB (structured progress data)
                    "synthesis_progress": {"completed": synth_succeeded, "total": total},
                },
            )
            logger.info(
                "Background TTS synthesis done for session %s: %d/%d succeeded, %d failed",
                session_id,
                synth_succeeded,
                total,
                failed_count,
            )

    except Exception:
        logger.exception("Background TTS synthesis failed for session %s", session_id)
        await _mark_session_failed(
            session_id,
            "synthesis_status",
            "synthesis_error",
            "Audio synthesis failed",
            repo_factory,
        )


# =============================================================================
# Image generation background task (019-story-pixel-images)
# =============================================================================


async def _update_image_generation_progress(
    session_id: str,
    completed: int,
    total: int,
    *,
    repo_factory: RepoFactory,
) -> None:
    """Update image generation progress in story_state JSONB (separate session)."""
    async with repo_factory() as repo:
        await repo.update_image_generation_progress(uuid.UUID(session_id), completed, total)


async def _generate_single_image(
    prompt: str,
    image_provider: IImageProvider,
    semaphore: asyncio.Semaphore,
) -> bytes | None:
    """Generate a single image with semaphore-controlled concurrency.

    Includes safety policy retry: if the first attempt fails (e.g. content
    policy rejection), retries once with a generalized character description.
    """
    async with semaphore:
        # First attempt with original prompt
        try:
            result = await image_provider.generate_image(prompt)
            if not result.image_bytes:
                logger.error("Image provider returned empty image bytes")
                return None
            return result.image_bytes
        except ImageQuotaError:
            raise  # Let caller handle quota exhaustion
        except Exception:
            logger.warning(
                "Image generation failed, retrying with generalized prompt: %s",
                prompt[:80],
                exc_info=True,
            )

        # Safety retry with generalized prompt (T042)
        fallback_prompt = _generalize_prompt(prompt)
        try:
            result = await image_provider.generate_image(fallback_prompt)
            if not result.image_bytes:
                return None
            return result.image_bytes
        except Exception:
            logger.warning(
                "Image generation retry also failed: %s", fallback_prompt[:80], exc_info=True
            )
            return None


def _generalize_prompt(prompt: str) -> str:
    """Replace specific character descriptions with generic ones for safety retry."""
    import re

    # Replace character-specific descriptions with generic ones
    generic = re.sub(
        r"(a |an |the )?\b(boy|girl|child|kid|person|man|woman)\b",
        "a brave little animal",
        prompt,
        flags=re.IGNORECASE,
    )
    # If no substitution happened, prepend a generic prefix (but avoid duplicating it)
    if generic == prompt:
        if prompt.startswith(PIXEL_ART_STYLE_PREFIX):
            # Already has prefix but regex didn't match — append generic subject
            # so retry uses a meaningfully different prompt
            generic = f"{prompt}, cute simple animal character"
        else:
            generic = f"{PIXEL_ART_STYLE_PREFIX}, centered cute pixel animal icon, {prompt}"
    return generic


def _downscale_to_16x16(image_bytes: bytes) -> bytes:
    """Downscale Imagen output to 16x16 then upscale 20x for crisp display."""
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    # LANCZOS for best quality downscale
    img_16 = img.resize((16, 16), Image.LANCZOS)
    # Convert to RGB (drop alpha if present)
    img_16 = img_16.convert("RGB")
    # Upscale 20x with nearest-neighbor to preserve pixel boundaries
    img_320 = img_16.resize((320, 320), Image.NEAREST)
    buf = io.BytesIO()
    img_320.save(buf, format="PNG")
    return buf.getvalue()


async def generate_images_background(
    session_id: str,
    llm: ILLMProvider,
    image_provider: IImageProvider,
    *,
    repo_factory: RepoFactory,
) -> None:
    """Background task: generate pixel art scene images for story turns.

    1. Call LLM to generate image prompts from story turns
    2. Call Imagen API in parallel (Semaphore(3)) for each prompt
    3. Upload images to storage, update turn image_path/scene_description
    4. Track progress in session state
    """
    try:
        async with repo_factory() as repo:
            session_uuid = uuid.UUID(session_id)
            db_session = await repo.get_session_with_turns(session_uuid)
            if not db_session:
                logger.error("Session %s not found in background image task", session_id)
                return

            turns_sorted = sorted(db_session.turns or [], key=lambda t: t.turn_number)
            if not turns_sorted:
                logger.warning("No turns found for session %s", session_id)
                return

            # Step 1: Generate image prompts using LLM
            start_time = time.monotonic()

            async def _on_cost(event_type: str, resp: LLMResponse) -> None:
                await _record_cost_event(session_id, event_type, resp, repo_factory=repo_factory)

            engine = StoryEngine(llm, cost_callback=_on_cost)
            try:
                prompt_items = await engine.generate_image_prompts(turns_sorted)
            except Exception:
                logger.exception("Failed to generate image prompts for session %s", session_id)
                await repo.update_session_state(
                    session_uuid,
                    {
                        "image_generation_status": "failed",
                        "image_generation_error": "圖片描述生成失敗，請稍後重試",
                    },
                )
                return

            llm_duration_ms = int((time.monotonic() - start_time) * 1000)
            total = len(prompt_items)
            if total == 0:
                logger.warning("LLM returned 0 image prompts for session %s", session_id)
                await repo.update_session_state(
                    session_uuid, {"image_generation_status": "completed"}
                )
                return

            logger.info(
                "Image prompt generation complete: %d prompts in %dms for session %s",
                total,
                llm_duration_ms,
                session_id,
            )

            # Update progress: 0/total
            await _update_image_generation_progress(session_id, 0, total, repo_factory=repo_factory)

            # Step 2: Generate images in parallel with Semaphore(3)
            storage = create_storage_service()
            semaphore = asyncio.Semaphore(3)

            # Build turn_number → turn mapping
            turn_map: dict[int, Any] = {t.turn_number: t for t in turns_sorted}

            quota_stop = asyncio.Event()

            async def _process_single_item(item: Any) -> _ImageResult:
                if quota_stop.is_set():
                    return _ImageResult(turn_number=item.turn_number, success=False)

                turn = turn_map.get(item.turn_number)
                if not turn:
                    logger.warning("Turn %d not found for image prompt, skipping", item.turn_number)
                    return _ImageResult(turn_number=item.turn_number, success=False)

                img_start = time.monotonic()
                try:
                    image_bytes = await _generate_single_image(
                        item.image_prompt, image_provider, semaphore
                    )
                except ImageQuotaError:
                    # T043: quota exceeded — signal other tasks to stop
                    quota_stop.set()
                    logger.warning(
                        "Image generation quota exceeded at turn %d in session %s",
                        item.turn_number,
                        session_id,
                    )
                    return _ImageResult(
                        turn_number=item.turn_number, success=False, quota_exceeded=True
                    )
                except Exception:
                    image_bytes = None

                img_duration_ms = int((time.monotonic() - img_start) * 1000)
                if img_duration_ms > 15_000:
                    logger.warning(
                        "Single image generation slow: %dms for turn %d in session %s",
                        img_duration_ms,
                        item.turn_number,
                        session_id,
                    )

                if image_bytes:
                    # Offload CPU-bound PIL resize to thread pool
                    image_bytes = await asyncio.to_thread(_downscale_to_16x16, image_bytes)
                    logger.debug(
                        "Image for turn %d: %dKB, generated in %dms",
                        item.turn_number,
                        len(image_bytes) // 1024,
                        img_duration_ms,
                    )
                    storage_key = f"story/{session_id}/images/{item.turn_number}.png"
                    try:
                        await storage.upload(
                            key=storage_key,
                            data=image_bytes,
                            content_type="image/png",
                        )
                        turn.image_path = storage_key
                        turn.scene_description = item.scene_description
                        await _record_image_cost_event(
                            session_id,
                            "gemini",
                            img_duration_ms,
                            repo_factory=repo_factory,
                        )
                        return _ImageResult(turn_number=item.turn_number, success=True)
                    except Exception:
                        logger.warning(
                            "Failed to upload image for turn %d in session %s",
                            item.turn_number,
                            session_id,
                            exc_info=True,
                        )
                        return _ImageResult(turn_number=item.turn_number, success=False)

                return _ImageResult(turn_number=item.turn_number, success=False)

            gather_results = await asyncio.gather(
                *(_process_single_item(item) for item in prompt_items),
                return_exceptions=True,
            )
            for i, result in enumerate(gather_results):
                if isinstance(result, Exception):
                    logger.error(
                        "Unexpected error in image task %d: %s",
                        i,
                        result,
                        exc_info=result,
                    )

            failed_count = sum(
                1 for r in gather_results if isinstance(r, _ImageResult) and not r.success
            )
            quota_exceeded = quota_stop.is_set()

            # Step 3: Finalize status
            images_succeeded = sum(1 for t in turns_sorted if getattr(t, "image_path", None))
            total_duration_ms = int((time.monotonic() - start_time) * 1000)

            if quota_exceeded:
                img_status = "failed"
                img_error: str | None = "圖片生成配額不足，已保留已完成的圖片，請稍後重試"
            elif images_succeeded == 0 and total > 0:
                img_status = "failed"
                img_error = "所有圖片生成失敗，請稍後重試"
            elif images_succeeded < total:
                img_status = "completed"
                img_error = f"部分圖片生成失敗 ({images_succeeded}/{total})"
            else:
                img_status = "completed"
                img_error = None

            # Commit image_path mutations on turn ORM objects + final session status
            await repo.update_session_state(
                session_uuid,
                {
                    "image_generation_status": img_status,
                    "image_generation_error": img_error,
                    # image_generation_progress in JSONB (structured progress data)
                    "image_generation_progress": {
                        "completed": images_succeeded,
                        "total": total,
                    },
                },
            )

            per_image_avg_ms = total_duration_ms // total if total else 0
            logger.info(
                "Background image generation done for session %s: "
                "%d/%d succeeded, %d failed, "
                "total=%dms, llm_prompt=%dms, per_image_avg=%dms",
                session_id,
                images_succeeded,
                total,
                failed_count,
                total_duration_ms,
                llm_duration_ms,
                per_image_avg_ms,
            )
            if total_duration_ms > 60_000:
                logger.warning(
                    "Image generation exceeded 60s target: %dms for session %s",
                    total_duration_ms,
                    session_id,
                )

    except Exception:
        logger.exception("Background image generation failed for session %s", session_id)
        await _mark_session_failed(
            session_id,
            "image_generation_status",
            "image_generation_error",
            "Image generation failed",
            repo_factory,
        )
