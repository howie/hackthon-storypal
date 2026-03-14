"""StoryPal REST API routes.

Feature: StoryPal — AI Interactive Story Companion

Endpoints for managing story templates and sessions.
Clean Architecture Sprint 2: all ORM queries moved to StoryRepositoryImpl.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from src.application.interfaces.llm_provider import ILLMProvider
from src.application.interfaces.tts_provider import ITTSProvider
from src.config import get_settings
from src.domain.entities.story import (
    ChildConfig,
    StorySessionStatus,
)
from src.domain.repositories.story_repository import IStoryRepository
from src.domain.services.story.content_generator import StoryContentGenerator
from src.domain.services.story.prompts import (
    build_child_config_story_context,
    build_custom_system_prompt,
    get_default_learning_scenarios,
    get_emotion_labels,
    get_value_labels,
)
from src.infrastructure.persistence.story_background_tasks import (
    generate_images_background,
    generate_story_background,
    synthesize_story_background,
)
from src.infrastructure.storage.factory import create_storage_service
from src.presentation.api.dependencies import (
    get_llm_providers,
    get_story_repository,
    get_tts_providers,
)
from src.presentation.api.middleware.auth import CurrentUserDep
from src.presentation.api.schemas.story_schemas import (
    ChildConfigSchema,
    CreateStorySessionRequest,
    DefaultsValueOption,
    GeneratedContentListResponse,
    ImageGenerationProgress,
    SceneInfoSchema,
    StoryCharacterSchema,
    StoryDefaultsResponse,
    StoryGeneratedContentResponse,
    StoryImageItem,
    StoryImageListResponse,
    StoryJobStatusResponse,
    StorySessionListResponse,
    StorySessionResponse,
    StoryTemplateListResponse,
    StoryTemplateResponse,
    StoryTurnResponse,
    SynthesisProgress,
    UpdateTurnContentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/story", tags=["StoryPal"])


# =============================================================================
# Helpers
# =============================================================================


def _db_template_to_response(m: Any) -> StoryTemplateResponse:
    """Convert DB template model to response (duck-typed)."""
    characters = [StoryCharacterSchema(**c) for c in (m.characters or [])]
    scenes = [SceneInfoSchema(**s) for s in (m.scenes or [])]
    return StoryTemplateResponse(
        id=str(m.id),
        name=m.name,
        description=m.description,
        category=m.category,
        target_age_min=m.target_age_min,
        target_age_max=m.target_age_max,
        language=m.language,
        characters=characters,
        scenes=scenes,
        opening_prompt=m.opening_prompt,
        system_prompt=m.system_prompt,
        is_default=m.is_default,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _session_to_response(
    m: Any,
    include_turns: bool = False,
) -> StorySessionResponse:
    """Convert DB session model to response (duck-typed)."""
    turns = None
    if include_turns and m.turns:
        turns = [
            StoryTurnResponse(
                id=str(t.id),
                session_id=str(t.session_id),
                turn_number=t.turn_number,
                turn_type=t.turn_type,
                character_name=t.character_name,
                content=t.content,
                audio_path=t.audio_path,
                image_path=getattr(t, "image_path", None),
                scene_description=getattr(t, "scene_description", None),
                choice_options=t.choice_options,
                child_choice=t.child_choice,
                bgm_scene=t.bgm_scene,
                created_at=t.created_at,
            )
            for t in sorted(m.turns, key=lambda x: x.turn_number)
        ]

    # Merge dedicated status columns back into story_state for frontend backward compat (BE-C#2).
    # The frontend reads s.story_state.generation_status / s.story_state.synthesis_status.
    story_state = dict(m.story_state or {})
    story_state["generation_status"] = m.generation_status
    story_state["synthesis_status"] = m.synthesis_status
    story_state["generation_error"] = m.generation_error
    story_state["synthesis_error"] = m.synthesis_error
    story_state["image_generation_status"] = getattr(m, "image_generation_status", None)
    story_state["image_generation_error"] = getattr(m, "image_generation_error", None)

    return StorySessionResponse(
        id=str(m.id),
        user_id=str(m.user_id),
        template_id=str(m.template_id) if m.template_id else None,
        title=m.title,
        language=m.language,
        status=m.status,
        story_state=story_state,
        characters_config=[StoryCharacterSchema(**c) for c in (m.characters_config or [])],
        child_config=ChildConfigSchema(**(m.child_config or {})),
        interaction_session_id=str(m.interaction_session_id) if m.interaction_session_id else None,
        current_scene=None,
        started_at=m.started_at,
        ended_at=m.ended_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
        turns=turns,
    )


# Available Gemini TTS voices for story narration
AVAILABLE_VOICES = ["Kore", "Puck", "Charon", "Fenrir", "Aoede", "Leda"]

# =============================================================================
# Defaults Endpoint
# =============================================================================


@router.get(
    "/defaults",
    response_model=StoryDefaultsResponse,
    summary="取得設定介面預設資料",
)
async def get_defaults(
    language: str = Query(default="zh-TW", description="Language for labels (zh-TW or en)"),
) -> StoryDefaultsResponse:
    """Return default options for the story setup form."""
    return StoryDefaultsResponse(
        default_learning_scenarios=get_default_learning_scenarios(language),
        values=[DefaultsValueOption(key=k, label=v) for k, v in get_value_labels(language).items()],
        emotions=[
            DefaultsValueOption(key=k, label=v) for k, v in get_emotion_labels(language).items()
        ],
        available_voices=AVAILABLE_VOICES,
    )


# =============================================================================
# Template Endpoints
# =============================================================================


@router.get(
    "/templates",
    response_model=StoryTemplateListResponse,
    summary="取得故事範本列表",
)
async def list_templates(
    _current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    category: str | None = Query(None, description="Filter by category"),
    language: str | None = Query(None, description="Filter by language"),
) -> StoryTemplateListResponse:
    """List available story templates from DB."""
    db_templates = await story_repo.list_templates(category=category, language=language)
    templates = [_db_template_to_response(m) for m in db_templates]
    return StoryTemplateListResponse(templates=templates, total=len(templates))


@router.get(
    "/templates/{template_id}",
    response_model=StoryTemplateResponse,
    summary="取得故事範本詳情",
)
async def get_template(
    template_id: str,
    _current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StoryTemplateResponse:
    """Get a specific story template by ID."""
    db_template = await story_repo.get_template(uuid.UUID(template_id))
    if not db_template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return _db_template_to_response(db_template)


# =============================================================================
# Session Endpoints
# =============================================================================


@router.post(
    "/sessions",
    response_model=StorySessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立新故事",
)
async def create_session(
    request: CreateStorySessionRequest,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StorySessionResponse:
    """Start a new interactive story session."""
    if not request.template_id and not request.child_config:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either template_id or child_config must be provided",
        )

    user_id = uuid.UUID(current_user.id)

    # Usage limit check: max stories per user
    settings = get_settings()
    session_count = await story_repo.count_completed_sessions(user_id)
    if session_count >= settings.max_stories_per_user:
        logger.warning(
            "USAGE LIMIT: User %s (%s) reached story limit (%d/%d). Please contact admin.",
            current_user.email,
            user_id,
            session_count,
            settings.max_stories_per_user,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USAGE_LIMIT_EXCEEDED",
                "message": (
                    f"已達故事上限 ({settings.max_stories_per_user} 個)，"
                    "請聯絡管理員 (GitHub Owner) 以取得更多配額。"
                ),
                "current_count": session_count,
                "max_allowed": settings.max_stories_per_user,
            },
        )

    # Resolve template
    template_id = None
    title = request.title or "新故事"
    characters_config: list[dict[str, Any]] = []
    db_tmpl = None

    if request.template_id:
        db_tmpl = await story_repo.get_template(uuid.UUID(request.template_id))
        if not db_tmpl:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template not found: {request.template_id}",
            )
        template_id = db_tmpl.id
        title = request.title or db_tmpl.name
        characters_config = [
            StoryCharacterSchema(**c).model_dump() for c in (db_tmpl.characters or [])
        ]

    # Override with request characters if provided
    if request.characters_config:
        characters_config = [c.model_dump() for c in request.characters_config]

    # Handle child_config — always build personalised system prompt
    child_config_data: dict[str, Any] = {}
    story_state: dict[str, Any] = {}

    if request.child_config:
        child_config_data = request.child_config.model_dump()
        child = ChildConfig(**child_config_data)
        content_lang = request.language
        system_prompt = build_custom_system_prompt(child, language=content_lang)

        # When template is also selected, append template context as style reference
        if request.template_id and db_tmpl:
            tmpl_context = db_tmpl.system_prompt or db_tmpl.description
            style_header = "## Story Style Reference" if content_lang == "en" else "## 故事風格參考"
            system_prompt += f"\n\n{style_header}\n{tmpl_context}"
            # Replace template protagonist with favorite_character if provided
            if child.favorite_character and characters_config:
                characters_config[0]["name"] = child.favorite_character

        story_state["system_prompt"] = system_prompt  # WS 互動模式用
        story_state["child_story_context"] = build_child_config_story_context(
            child, language=content_lang
        )  # 靜態故事用
        if not request.title:
            if content_lang == "en":
                title = f"{child.favorite_character or 'Story Sprite'}'s Adventure"
            else:
                title = f"{child.favorite_character or '故事精靈'}的冒險"

    # Store voice/story mode settings in story_state JSONB
    if request.voice_mode:
        story_state["voice_mode"] = request.voice_mode
    if request.story_mode:
        story_state["story_mode"] = request.story_mode
    if request.content_extras:
        story_state["content_extras"] = request.content_extras
    if request.tts_provider:
        story_state["tts_provider"] = request.tts_provider

    db_session = await story_repo.create_session(
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "template_id": template_id,
            "title": title,
            "language": request.language,
            "status": StorySessionStatus.ACTIVE.value,
            "story_state": story_state,
            "characters_config": characters_config,
            "child_config": child_config_data,
            "started_at": datetime.now(UTC),
        }
    )
    return _session_to_response(db_session)


@router.get(
    "/sessions",
    response_model=StorySessionListResponse,
    summary="取得故事列表",
)
async def list_sessions(
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    session_status: str | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> StorySessionListResponse:
    """List story sessions for the current user."""
    user_id = uuid.UUID(current_user.id)
    sessions_list, total = await story_repo.list_sessions(
        user_id=user_id,
        status=session_status,
        page=page,
        page_size=page_size,
    )
    return StorySessionListResponse(
        sessions=[_session_to_response(s) for s in sessions_list],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=StorySessionResponse,
    summary="取得故事詳情",
)
async def get_session(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StorySessionResponse:
    """Get story session details with all turns."""
    user_id = uuid.UUID(current_user.id)
    db_session = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _session_to_response(db_session, include_turns=True)


@router.post(
    "/sessions/{session_id}/resume",
    response_model=StorySessionResponse,
    summary="繼續故事",
)
async def resume_session(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StorySessionResponse:
    """Resume a paused story session."""
    user_id = uuid.UUID(current_user.id)
    db_session = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if db_session.status == StorySessionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session already completed"
        )

    db_session = await story_repo.update_session(
        uuid.UUID(session_id), user_id, {"status": StorySessionStatus.ACTIVE.value}
    )
    return _session_to_response(db_session, include_turns=True)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="刪除故事",
)
async def delete_session(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> None:
    """Delete a story session and its turns."""
    user_id = uuid.UUID(current_user.id)
    sess = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Clean up GCS audio/image files before deleting DB records (CASCADE would orphan them)
    storage_paths: list[str] = []
    for t in sess.turns or []:
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
                logger.warning("Failed to delete storage file: %s", path)

    await story_repo.delete_session(uuid.UUID(session_id), user_id)


# =============================================================================
# Generated Content Endpoints
# =============================================================================


def _content_model_to_response(m: Any) -> StoryGeneratedContentResponse:
    return StoryGeneratedContentResponse(
        id=str(m.id),
        session_id=str(m.session_id),
        content_type=m.content_type,
        content_data=m.content_data or {},
        created_at=m.created_at,
    )


def _get_default_llm(llm_providers: dict[str, ILLMProvider]) -> ILLMProvider:
    """Get the best available LLM provider (prefer gemini)."""
    for name in ("gemini", "openai", "azure-openai"):
        if name in llm_providers:
            return llm_providers[name]
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No LLM provider configured",
    )


@router.post(
    "/sessions/{session_id}/song",
    response_model=StoryGeneratedContentResponse,
    summary="生成主題兒歌",
)
async def generate_song(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    llm_providers: Annotated[dict[str, ILLMProvider], Depends(get_llm_providers)],
) -> StoryGeneratedContentResponse:
    """Generate a children's song for the session."""
    user_id = uuid.UUID(current_user.id)
    db_session = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    generator = StoryContentGenerator(_get_default_llm(llm_providers))
    domain_session = _db_to_domain_session(db_session)
    content = await generator.generate_song(domain_session)

    db_content = await story_repo.create_generated_content(
        {
            "id": content.id,
            "session_id": content.session_id,
            "content_type": content.content_type,
            "content_data": content.content_data,
        }
    )
    return _content_model_to_response(db_content)


@router.post(
    "/sessions/{session_id}/qa",
    response_model=StoryGeneratedContentResponse,
    summary="生成故事 Q&A 互動",
)
async def generate_qa(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    llm_providers: Annotated[dict[str, ILLMProvider], Depends(get_llm_providers)],
) -> StoryGeneratedContentResponse:
    """Generate Q&A questions for the session (idempotent)."""
    user_id = uuid.UUID(current_user.id)
    session_uuid = uuid.UUID(session_id)
    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Idempotency: return existing QA if already generated
    existing = await story_repo.list_generated_content(session_uuid, user_id)
    existing_qa = [c for c in existing if c.content_type == "qa"]
    if existing_qa:
        return _content_model_to_response(existing_qa[0])

    generator = StoryContentGenerator(_get_default_llm(llm_providers))
    domain_session = _db_to_domain_session(db_session)
    content = await generator.generate_qa(domain_session)

    db_content = await story_repo.create_generated_content(
        {
            "id": content.id,
            "session_id": content.session_id,
            "content_type": content.content_type,
            "content_data": content.content_data,
        }
    )
    return _content_model_to_response(db_content)


@router.post(
    "/sessions/{session_id}/interactive-choices",
    response_model=StoryGeneratedContentResponse,
    summary="生成故事走向選擇互動",
)
async def generate_interactive_choices(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    llm_providers: Annotated[dict[str, ILLMProvider], Depends(get_llm_providers)],
) -> StoryGeneratedContentResponse:
    """Generate interactive choice nodes for the session."""
    user_id = uuid.UUID(current_user.id)
    db_session = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    generator = StoryContentGenerator(_get_default_llm(llm_providers))
    domain_session = _db_to_domain_session(db_session)
    content = await generator.generate_interactive_choices(domain_session)

    db_content = await story_repo.create_generated_content(
        {
            "id": content.id,
            "session_id": content.session_id,
            "content_type": content.content_type,
            "content_data": content.content_data,
        }
    )
    return _content_model_to_response(db_content)


@router.get(
    "/sessions/{session_id}/content",
    response_model=GeneratedContentListResponse,
    summary="取得所有已生成內容",
)
async def list_generated_content(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> GeneratedContentListResponse:
    """List all generated content for a session."""
    user_id = uuid.UUID(current_user.id)
    if not await story_repo.get_session(uuid.UUID(session_id), user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    contents = await story_repo.list_generated_content(uuid.UUID(session_id), user_id)
    return GeneratedContentListResponse(
        session_id=session_id,
        contents=[_content_model_to_response(c) for c in contents],
    )


# =============================================================================
# Static Playback Endpoints (純播放模式)
# =============================================================================


def _get_default_tts(tts_providers: dict[str, ITTSProvider]) -> ITTSProvider | None:
    """Get the best available TTS provider (prefer gemini-pro)."""
    for name in ("gemini-pro", "gemini-flash", "gcp", "azure", "elevenlabs"):
        if name in tts_providers:
            return tts_providers[name]
    return None


async def _resolve_template(db_session: Any, story_repo: IStoryRepository) -> Any:
    """Resolve the story template for a session from DB or session data."""
    if db_session.template_id:
        db_tmpl = await story_repo.get_template(db_session.template_id)
        if db_tmpl:
            from src.domain.entities.story import (
                SceneInfo,
                StoryCharacter,
                StoryTemplate,
            )

            # Use child_story_context for static story generation (no interactive rules).
            # Falls back to db template system_prompt when no child_config was set.
            story_state = db_session.story_state or {}
            effective_prompt = story_state.get("child_story_context") or db_tmpl.system_prompt

            return StoryTemplate(
                id=db_tmpl.id,
                name=db_tmpl.name,
                description=db_tmpl.description,
                category=db_tmpl.category,
                target_age_min=db_tmpl.target_age_min,
                target_age_max=db_tmpl.target_age_max,
                language=db_tmpl.language,
                characters=[
                    StoryCharacter(**c)
                    for c in (db_session.characters_config or db_tmpl.characters or [])
                ],
                scenes=[SceneInfo(**s) for s in (db_tmpl.scenes or [])],
                opening_prompt=db_tmpl.opening_prompt,
                system_prompt=effective_prompt,
                is_default=db_tmpl.is_default,
            )

    # Fallback: build template from session data (custom prompt scenario)
    from src.domain.entities.story import (
        StoryCategory,
        StoryCharacter,
        StoryTemplate,
    )

    chars = [StoryCharacter(**c) for c in (db_session.characters_config or [])]
    story_state = db_session.story_state or {}
    # Use child_story_context for static story generation; fall back to system_prompt
    # (WS interactive prompt) only when child_story_context is absent.
    system_prompt = story_state.get("child_story_context") or story_state.get("system_prompt", "")
    return StoryTemplate(
        name=db_session.title,
        description=system_prompt or db_session.title,
        category=StoryCategory.ADVENTURE,
        target_age_min=3,
        target_age_max=8,
        language=db_session.language,
        characters=chars,
        scenes=[],
        opening_prompt=story_state.get("opening_prompt", ""),
        system_prompt=system_prompt,
    )


def _build_status_response(db_session: Any) -> StoryJobStatusResponse:
    """Build a StoryJobStatusResponse from a DB session model.

    Reads status from dedicated columns (BE-C#2); synthesis_progress stays in JSONB.
    """
    state = db_session.story_state or {}
    turns = db_session.turns or []
    return StoryJobStatusResponse(
        session_id=str(db_session.id),
        generation_status=db_session.generation_status,
        synthesis_status=db_session.synthesis_status,
        generation_error=db_session.generation_error,
        synthesis_error=db_session.synthesis_error,
        synthesis_progress=SynthesisProgress(**state.get("synthesis_progress", {})),
        turns_count=len(turns),
        audio_ready_count=sum(1 for t in turns if t.audio_path),
        image_generation_status=getattr(db_session, "image_generation_status", None),
        image_generation_progress=ImageGenerationProgress(
            **state.get("image_generation_progress", {})
        ),
        image_generation_error=getattr(db_session, "image_generation_error", None),
    )


@router.post(
    "/sessions/{session_id}/generate",
    response_model=StoryJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="生成完整故事內容（純播放模式）",
)
async def generate_story(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    llm_providers: Annotated[dict[str, ILLMProvider], Depends(get_llm_providers)],
) -> StoryJobStatusResponse:
    """Trigger background story generation. Returns 202 immediately.

    Poll GET /sessions/{session_id}/status for progress.
    """
    user_id = uuid.UUID(current_user.id)
    session_uuid = uuid.UUID(session_id)

    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Atomic compare-and-swap: only one concurrent request can set "generating"
    if not await story_repo.set_session_generating(session_uuid, user_id):
        # Already generating — return current status without launching a new task
        return _build_status_response(db_session)

    # Re-fetch to get the state written by the atomic SQL
    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)

    template = await _resolve_template(db_session, story_repo)
    llm = _get_default_llm(llm_providers)
    language = db_session.language or "繁體中文"

    story_state = db_session.story_state or {}
    include_choice_points = story_state.get("story_mode") == "branching"
    asyncio.create_task(
        generate_story_background(
            session_id,
            template,
            language,
            llm,
            include_choice_points=include_choice_points,
        )
    )

    return _build_status_response(db_session)


@router.post(
    "/sessions/{session_id}/synthesize",
    response_model=StoryJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="合成故事音訊（純播放模式）",
)
async def synthesize_story(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    tts_providers: Annotated[dict[str, ITTSProvider], Depends(get_tts_providers)],
) -> StoryJobStatusResponse:
    """Trigger background TTS synthesis. Returns 202 immediately.

    Poll GET /sessions/{session_id}/status for progress.
    """
    user_id = uuid.UUID(current_user.id)
    session_uuid = uuid.UUID(session_id)

    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if not db_session.turns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No story turns found. Call /generate first.",
        )

    tts_provider_name = (db_session.story_state or {}).get("tts_provider", "gemini-pro")
    tts = tts_providers.get(tts_provider_name) or _get_default_tts(tts_providers)
    if not tts:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No TTS provider configured",
        )

    # Build character → voice_id mapping
    chars_config = db_session.characters_config or []
    char_voices: dict[str, str] = {}
    for c in chars_config:
        if isinstance(c, dict) and c.get("name") and c.get("voice_id"):
            char_voices[c["name"]] = c["voice_id"]

    turns_to_synth = list(db_session.turns or [])

    # Atomic guard: avoid duplicate task launch (UPDATE … WHERE … RETURNING)
    if not await story_repo.set_session_synthesizing(session_uuid, user_id, len(turns_to_synth)):
        return _build_status_response(db_session)

    # Re-fetch to get updated state for response
    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)

    asyncio.create_task(
        synthesize_story_background(
            session_id, char_voices, tts, tts_provider_name=tts_provider_name
        )
    )

    return _build_status_response(db_session)


@router.get(
    "/sessions/{session_id}/turns/{turn_id}/audio",
    summary="串流故事段落音訊",
)
async def get_turn_audio(
    session_id: str,
    turn_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> Response:
    """Stream the audio file for a specific story turn."""
    user_id = uuid.UUID(current_user.id)

    # Verify session ownership
    sess = await story_repo.get_session(uuid.UUID(session_id), user_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get turn
    turn = await story_repo.get_turn(uuid.UUID(turn_id), uuid.UUID(session_id))
    if not turn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

    if not turn.audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not synthesized yet. Call /synthesize first.",
        )

    storage = create_storage_service()
    logger.info("Audio download: storage=%s key=%s", type(storage).__name__, turn.audio_path)
    try:
        data = await storage.download(turn.audio_path)
    except FileNotFoundError:
        logger.warning(
            "Audio file missing in storage: storage=%s key=%s session=%s turn=%s",
            type(storage).__name__,
            turn.audio_path,
            session_id,
            turn_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found in storage",
        ) from None

    return Response(content=data, media_type="audio/mpeg")


# =============================================================================
# Image Generation Endpoints (019-story-pixel-images)
# =============================================================================


@router.post(
    "/sessions/{session_id}/generate-images",
    response_model=StoryJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="觸發場景圖片生成",
)
async def generate_images(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
    llm_providers: Annotated[dict[str, ILLMProvider], Depends(get_llm_providers)],
) -> StoryJobStatusResponse:
    """Trigger background image generation. Returns 202 immediately.

    Poll GET /sessions/{session_id}/status for progress.
    """
    user_id = uuid.UUID(current_user.id)
    session_uuid = uuid.UUID(session_id)

    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if db_session.generation_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Story text generation not yet completed. Call /generate first.",
        )

    if not db_session.turns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No story turns found.",
        )

    # Atomic guard: avoid duplicate task launch
    if not await story_repo.set_session_image_generating(session_uuid, user_id, 0):
        return _build_status_response(db_session)

    # Re-fetch to get updated state
    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)

    llm = _get_default_llm(llm_providers)

    # Create image provider
    from src.infrastructure.providers.image.factory import ImageProviderFactory

    try:
        image_provider = ImageProviderFactory.create_default()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Image provider not configured: {e}",
        ) from None

    asyncio.create_task(generate_images_background(session_id, llm, image_provider))

    return _build_status_response(db_session)


@router.get(
    "/sessions/{session_id}/images",
    response_model=StoryImageListResponse,
    summary="取得故事場景圖片列表",
)
async def list_session_images(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StoryImageListResponse:
    """List all scene images for a story session."""
    user_id = uuid.UUID(current_user.id)
    db_session = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    images = []
    for t in sorted(db_session.turns or [], key=lambda x: x.turn_number):
        image_path = getattr(t, "image_path", None)
        if image_path:
            images.append(
                StoryImageItem(
                    turn_number=t.turn_number,
                    image_url=f"/files/{image_path}",
                    scene_description=getattr(t, "scene_description", "") or "",
                )
            )

    return StoryImageListResponse(images=images)


@router.get(
    "/sessions/{session_id}/turns/{turn_id}/image",
    summary="取得故事段落場景圖片",
)
async def get_turn_image(
    session_id: str,
    turn_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> Response:
    """Stream the scene image for a specific story turn."""
    user_id = uuid.UUID(current_user.id)

    sess = await story_repo.get_session(uuid.UUID(session_id), user_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    turn = await story_repo.get_turn(uuid.UUID(turn_id), uuid.UUID(session_id))
    if not turn or str(turn.session_id) != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

    image_path = getattr(turn, "image_path", None)
    if not image_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turn has no scene image",
        )

    storage = create_storage_service()
    try:
        data = await storage.download(image_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found in storage",
        ) from None

    return Response(content=data, media_type="image/png")


# =============================================================================
# Download full session audio
# =============================================================================


@router.get(
    "/sessions/{session_id}/audio/download",
    summary="下載完整故事音訊",
)
async def download_session_audio(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> Response:
    """Concatenate all turn audio files into a single MP3 download."""
    try:
        user_id = uuid.UUID(current_user.id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity"
        ) from None

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID format: {session_id}",
        ) from None

    # Verify session ownership and load turns
    db_session = await story_repo.get_session_with_turns(session_uuid, user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Filter playable turns with audio, sorted by turn_number
    audio_turns = sorted(
        [
            t
            for t in (db_session.turns or [])
            if t.audio_path and t.turn_type not in ("child_response", "question")
        ],
        key=lambda t: t.turn_number,
    )
    if not audio_turns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audio available for this session",
        )

    try:
        storage = create_storage_service()
    except Exception:
        logger.error("Failed to initialise storage service for audio download", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable",
        ) from None

    chunks: list[bytes] = []
    for turn in audio_turns:
        try:
            data = await storage.download(turn.audio_path)
            if data:
                chunks.append(data)
        except FileNotFoundError:
            logger.warning("Audio file missing for turn %s: %s", turn.id, turn.audio_path)
        except Exception:
            logger.warning(
                "Failed to download audio for turn %s (path=%s)",
                turn.id,
                turn.audio_path,
                exc_info=True,
            )

    if not chunks:
        logger.warning(
            "All audio downloads failed for session %s — attempted %d turns: %s",
            session_id,
            len(audio_turns),
            [(str(t.id), t.audio_path) for t in audio_turns],
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio files not found in storage",
        )

    combined = b"".join(chunks)
    raw_title = (db_session.title or "story").replace('"', "")
    # RFC 5987: ASCII fallback + UTF-8 encoded filename for non-ASCII characters
    ascii_fallback = "story.mp3"
    encoded_name = quote(raw_title) + ".mp3"
    return Response(
        content=combined,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_name}"
            )
        },
    )


# =============================================================================
# Update turn content
# =============================================================================


@router.patch(
    "/sessions/{session_id}/turns/{turn_id}",
    response_model=StoryTurnResponse,
    summary="更新故事段落文字",
)
async def update_turn_content(
    session_id: str,
    turn_id: str,
    body: UpdateTurnContentRequest,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StoryTurnResponse:
    """Update the text content of a story turn. Clears existing audio if present."""
    user_id = uuid.UUID(current_user.id)
    session_uuid = uuid.UUID(session_id)
    turn_uuid = uuid.UUID(turn_id)

    # Verify session ownership
    if not await story_repo.get_session(session_uuid, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Update content (captures stale paths atomically, then clears them in DB)
    turn, stale_paths = await story_repo.update_turn_content(turn_uuid, session_uuid, body.content)
    if not turn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

    # Delete stale files from storage (infrastructure side-effect)
    if stale_paths:
        storage = create_storage_service()
        results = await asyncio.gather(
            *(storage.delete(path) for path in stale_paths),
            return_exceptions=True,
        )
        for path, result in zip(stale_paths, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("Failed to delete old file for turn %s: %s", turn_id, path)

    return StoryTurnResponse(
        id=str(turn.id),
        session_id=str(turn.session_id),
        turn_number=turn.turn_number,
        turn_type=turn.turn_type,
        character_name=turn.character_name,
        content=turn.content,
        audio_path=turn.audio_path,
        image_path=getattr(turn, "image_path", None),
        scene_description=getattr(turn, "scene_description", None),
        choice_options=turn.choice_options,
        child_choice=turn.child_choice,
        bgm_scene=turn.bgm_scene,
        created_at=turn.created_at,
    )


# =============================================================================
# Async Job Status Endpoint
# =============================================================================


@router.get(
    "/sessions/{session_id}/status",
    response_model=StoryJobStatusResponse,
    summary="查詢故事生成/合成狀態",
)
async def get_session_status(
    session_id: str,
    current_user: CurrentUserDep,
    story_repo: Annotated[IStoryRepository, Depends(get_story_repository)],
) -> StoryJobStatusResponse:
    """Poll this endpoint to track generation/synthesis progress."""
    user_id = uuid.UUID(current_user.id)
    db_session = await story_repo.get_session_with_turns(uuid.UUID(session_id), user_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _build_status_response(db_session)


# =============================================================================
# Domain conversion helper
# =============================================================================


def _db_to_domain_session(m: Any) -> Any:
    """Convert DB model to a lightweight domain StorySession for generators."""
    from src.domain.entities.story import ChildConfig as DomainChildConfig
    from src.domain.entities.story import StorySession, StoryTurn, StoryTurnType

    child_data = m.child_config or {}
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
    if m.turns:
        for t in sorted(m.turns, key=lambda x: x.turn_number):
            try:
                turn_type = StoryTurnType(t.turn_type)
            except ValueError:
                turn_type = StoryTurnType.NARRATION
            turns.append(
                StoryTurn(
                    session_id=m.id,
                    turn_number=t.turn_number,
                    turn_type=turn_type,
                    content=t.content,
                    id=t.id,
                    character_name=t.character_name,
                    created_at=t.created_at,
                )
            )

    return StorySession(
        id=m.id,
        title=m.title,
        language=m.language,
        user_id=str(m.user_id),
        template_id=m.template_id,
        story_state=m.story_state or {},
        child_config=child,
        turns=turns,
        started_at=m.started_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )
