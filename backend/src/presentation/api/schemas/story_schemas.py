"""Pydantic schemas for StoryPal API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Character & Scene Schemas
# =============================================================================


class StoryCharacterSchema(BaseModel):
    """Character configuration."""

    name: str
    description: str
    voice_provider: str
    voice_id: str
    voice_settings: dict[str, Any] = Field(default_factory=dict)
    emotion: str = "neutral"


class SceneInfoSchema(BaseModel):
    """Scene information."""

    name: str
    description: str
    bgm_prompt: str = ""
    mood: str = "neutral"


# =============================================================================
# Template Schemas
# =============================================================================


class StoryTemplateResponse(BaseModel):
    """Story template response."""

    id: str
    name: str
    description: str
    category: str
    target_age_min: int
    target_age_max: int
    language: str
    characters: list[StoryCharacterSchema]
    scenes: list[SceneInfoSchema]
    opening_prompt: str
    system_prompt: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class StoryTemplateListResponse(BaseModel):
    """List of story templates."""

    templates: list[StoryTemplateResponse]
    total: int


# =============================================================================
# Child Config Schema
# =============================================================================


class ChildConfigSchema(BaseModel):
    """Child personalisation config stored in story_sessions.child_config."""

    age: int = Field(default=4, ge=1, le=8)
    learning_goals: str = ""
    selected_values: list[str] = Field(default_factory=list)
    selected_emotions: list[str] = Field(default_factory=list)
    favorite_character: str = ""
    child_name: str = "小朋友"
    voice_id: str | None = None


# =============================================================================
# Generated Content Schemas
# =============================================================================


class SongContentData(BaseModel):
    """Content data for generated songs."""

    lyrics: str = ""
    suno_prompt: str = ""
    generated_at: datetime | None = None


class QAQuestion(BaseModel):
    """A single Q&A question."""

    order: int
    question: str
    hint: str = ""
    encouragement: str = ""


class QAContentData(BaseModel):
    """Content data for generated Q&A."""

    questions: list[QAQuestion] = Field(default_factory=list)
    closing: str = ""
    timeout_seconds: int = 5
    generated_at: datetime | None = None


class ChoiceNode(BaseModel):
    """A single interactive choice node."""

    order: int
    prompt: str
    options: list[str] = Field(default_factory=list)
    timeout_seconds: int = 5
    timeout_hint: str = ""


class InteractiveChoicesContentData(BaseModel):
    """Content data for interactive story choices."""

    script: str = ""
    choice_nodes: list[ChoiceNode] = Field(default_factory=list)
    generated_at: datetime | None = None


class DefaultsValueOption(BaseModel):
    """A key-label pair for value/emotion options."""

    key: str
    label: str


class StoryDefaultsResponse(BaseModel):
    """Response for GET /defaults — setup form options."""

    default_learning_scenarios: list[str]
    values: list[DefaultsValueOption]
    emotions: list[DefaultsValueOption]
    available_voices: list[str]


class StoryGeneratedContentResponse(BaseModel):
    """Response schema for story_generated_content."""

    id: str
    session_id: str
    content_type: str
    content_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class GeneratedContentListResponse(BaseModel):
    """Response for GET /sessions/{id}/content."""

    session_id: str
    contents: list[StoryGeneratedContentResponse]


# =============================================================================
# Session Schemas
# =============================================================================


class UpdateTurnContentRequest(BaseModel):
    """Request to update the text content of a story turn."""

    content: str = Field(..., min_length=1, max_length=5000)


class CreateStorySessionRequest(BaseModel):
    """Request to create a new story session."""

    template_id: str | None = None
    title: str | None = None
    language: str = "zh-TW"
    characters_config: list[StoryCharacterSchema] | None = None
    custom_prompt: str | None = None
    child_config: ChildConfigSchema | None = None
    voice_mode: str | None = None  # 'multi_role' | 'single_role'
    story_mode: str | None = None  # 'linear' | 'branching'
    content_extras: list[str] = Field(default_factory=list)
    tts_provider: str | None = None  # 'gemini-flash' | 'gemini-pro', default gemini-pro


class StoryTurnResponse(BaseModel):
    """A single story turn."""

    id: str
    session_id: str
    turn_number: int
    turn_type: str
    character_name: str | None = None
    content: str
    audio_path: str | None = None
    image_path: str | None = None
    scene_description: str | None = None
    choice_options: list[str] | None = None
    child_choice: str | None = None
    bgm_scene: str | None = None
    created_at: datetime


class StorySessionResponse(BaseModel):
    """Story session response."""

    id: str
    user_id: str
    template_id: str | None = None
    title: str
    language: str
    status: str
    story_state: dict[str, Any] = Field(default_factory=dict)
    characters_config: list[StoryCharacterSchema] = Field(default_factory=list)
    child_config: ChildConfigSchema = Field(default_factory=ChildConfigSchema)
    interaction_session_id: str | None = None
    current_scene: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    turns: list[StoryTurnResponse] | None = None


class StorySessionListResponse(BaseModel):
    """List of story sessions."""

    sessions: list[StorySessionResponse]
    total: int
    page: int
    page_size: int


class TutorGame(BaseModel):
    """A single tutor game definition."""

    id: str
    name: str
    description: str
    min_age: int
    max_age: int


class TutorV2vConfig(BaseModel):
    """Gemini Live API configuration for US5 適齡萬事通 v2v mode.

    NOTE: The Google AI API key is intentionally excluded from this response.
    The Gemini Live WebSocket connection should be proxied through the backend
    so that credentials are never exposed to the client.
    TODO: Implement backend WebSocket proxy for Gemini Live API (BE-C#1).
    """

    ws_url: str
    model: str
    voice: str
    available_voices: list[str]
    system_prompt: str
    available_games: list[TutorGame] = Field(default_factory=list)


# =============================================================================
# Async Job Status Schemas
# =============================================================================


class SynthesisProgress(BaseModel):
    """TTS synthesis progress tracker."""

    completed: int = 0
    total: int = 0


class ImageGenerationProgress(BaseModel):
    """Image generation progress tracker."""

    completed: int = 0
    total: int = 0


class StoryJobStatusResponse(BaseModel):
    """Response for GET /sessions/{id}/status — async job polling."""

    session_id: str
    generation_status: str | None = None
    synthesis_status: str | None = None
    generation_error: str | None = None
    synthesis_error: str | None = None
    synthesis_progress: SynthesisProgress = Field(default_factory=SynthesisProgress)
    turns_count: int = 0
    audio_ready_count: int = 0
    # Image generation fields (019-story-pixel-images)
    image_generation_status: str | None = None
    image_generation_progress: ImageGenerationProgress = Field(
        default_factory=ImageGenerationProgress
    )
    image_generation_error: str | None = None


class StoryImageItem(BaseModel):
    """A single scene image item."""

    turn_number: int
    image_url: str
    scene_description: str


class StoryImageListResponse(BaseModel):
    """Response for GET /sessions/{id}/images."""

    images: list[StoryImageItem]
