"""Tutor (適齡萬事通) REST API routes.

Separated from StoryPal routes — Tutor is an independent feature with its own
``/api/v1/tutor`` prefix.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.domain.services.story.prompts import build_tutor_system_prompt, get_available_games
from src.presentation.api.middleware.auth import CurrentUserDep
from src.presentation.api.schemas.story_schemas import TutorGame, TutorV2vConfig

router = APIRouter(prefix="/tutor", tags=["Tutor"])

_GEMINI_LIVE_WS_URL = (
    "wss://generativelanguage.googleapis.com"
    "/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
)

_TUTOR_AVAILABLE_VOICES = ["Kore", "Puck", "Aoede", "Charon", "Fenrir", "Leda"]


@router.get(
    "/games",
    response_model=list[TutorGame],
    summary="取得指定年齡可玩的遊戲列表",
)
async def get_tutor_games(
    _current_user: CurrentUserDep,
    child_age: int = Query(default=4, ge=1, le=8),
) -> list[TutorGame]:
    """Return the list of games available for the given child age."""
    games = get_available_games(child_age)
    return [TutorGame(**g) for g in games]


@router.get(
    "/v2v-config",
    response_model=TutorV2vConfig,
    summary="取得 US5 適齡萬事通 Gemini Live v2v 連線設定",
)
async def get_tutor_v2v_config(
    _current_user: CurrentUserDep,
    child_age: int = Query(default=4, ge=1, le=8),
    voice: str = Query(default="Kore"),
    game_type: str | None = Query(default=None),
) -> TutorV2vConfig:
    """Return Gemini Live API config for the tutor v2v WebSocket connection.

    SECURITY NOTE (BE-C#1): The Google AI API key is NOT returned in this
    response to prevent credential exposure in browser DevTools.
    The API key is validated server-side only to confirm it is configured.
    """
    from src.config import get_settings

    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Set GEMINI_API_KEY env var.",
        )

    system_prompt = build_tutor_system_prompt(child_age, game_type=game_type)
    games = get_available_games(child_age)

    # NOTE: api_key is intentionally omitted from the response (BE-C#1).
    return TutorV2vConfig(
        ws_url=_GEMINI_LIVE_WS_URL,
        model=settings.gemini_live_model,
        voice=voice if voice in _TUTOR_AVAILABLE_VOICES else "Kore",
        available_voices=_TUTOR_AVAILABLE_VOICES,
        system_prompt=system_prompt,
        available_games=[TutorGame(**g) for g in games],
    )
