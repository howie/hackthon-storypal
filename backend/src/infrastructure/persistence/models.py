import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.entities.interaction_enums import InteractionMode, SessionStatus
from src.infrastructure.persistence.database import Base


class User(Base):
    """User model for Google SSO authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =============================================================================
# Interaction Models
# =============================================================================


class InteractionSessionModel(Base):
    """SQLAlchemy model for interaction sessions."""

    __tablename__ = "interaction_sessions"
    __table_args__ = (
        Index("idx_session_user_id", "user_id"),
        Index("idx_session_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[InteractionMode] = mapped_column(
        Enum(
            InteractionMode,
            name="interaction_mode",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    provider_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    user_role: Mapped[str] = mapped_column(String(100), nullable=False, default="使用者")
    ai_role: Mapped[str] = mapped_column(String(100), nullable=False, default="AI 助理")
    scenario_context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    turns: Mapped[list["ConversationTurnModel"]] = relationship(
        "ConversationTurnModel", back_populates="session", cascade="all, delete-orphan"
    )


class ConversationTurnModel(Base):
    """SQLAlchemy model for conversation turns."""

    __tablename__ = "conversation_turns"
    __table_args__ = (
        Index("idx_turn_session_id", "session_id"),
        Index("idx_turn_session_number", "session_id", "turn_number"),
        UniqueConstraint("session_id", "turn_number", name="uq_turn_session_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interaction_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    user_audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    interrupted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session: Mapped["InteractionSessionModel"] = relationship(
        "InteractionSessionModel", back_populates="turns"
    )
    latency_metrics: Mapped["LatencyMetricsModel | None"] = relationship(
        "LatencyMetricsModel", back_populates="turn", uselist=False, cascade="all, delete-orphan"
    )


class LatencyMetricsModel(Base):
    """SQLAlchemy model for latency metrics."""

    __tablename__ = "latency_metrics"
    __table_args__ = (Index("idx_latency_turn_id", "turn_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    stt_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_ttfb_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    realtime_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    turn: Mapped["ConversationTurnModel"] = relationship(
        "ConversationTurnModel", back_populates="latency_metrics"
    )


# =============================================================================
# StoryPal Models
# =============================================================================


class StoryTemplateModel(Base):
    """Pre-built story template for StoryPal."""

    __tablename__ = "story_templates"
    __table_args__ = (
        Index("idx_story_template_category", "category"),
        Index("idx_story_template_language", "language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    target_age_min: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    target_age_max: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-TW")
    characters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scenes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    opening_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sessions: Mapped[list["StorySessionModel"]] = relationship(
        "StorySessionModel", back_populates="template"
    )


class StorySessionModel(Base):
    """Active or completed interactive story session."""

    __tablename__ = "story_sessions"
    __table_args__ = (
        Index("idx_story_session_user", "user_id"),
        Index("idx_story_session_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-TW")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    story_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    characters_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=list)
    child_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}", default=dict
    )
    interaction_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interaction_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    generation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    synthesis_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    synthesis_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_generation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    image_generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    template: Mapped["StoryTemplateModel | None"] = relationship(
        "StoryTemplateModel", back_populates="sessions"
    )
    interaction_session: Mapped["InteractionSessionModel | None"] = relationship(
        "InteractionSessionModel"
    )
    turns: Mapped[list["StoryTurnModel"]] = relationship(
        "StoryTurnModel", back_populates="session", cascade="all, delete-orphan"
    )
    generated_contents: Mapped[list["StoryGeneratedContentModel"]] = relationship(
        "StoryGeneratedContentModel", back_populates="session", cascade="all, delete-orphan"
    )
    cost_events: Mapped[list["StoryCostEventModel"]] = relationship(
        "StoryCostEventModel", back_populates="session", cascade="all, delete-orphan"
    )


class StoryTurnModel(Base):
    """Individual story segment or turn within a session."""

    __tablename__ = "story_turns"
    __table_args__ = (
        Index("idx_story_turn_session", "session_id"),
        Index("idx_story_turn_number", "session_id", "turn_number"),
        UniqueConstraint("session_id", "turn_number", name="uq_story_turn_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_type: Mapped[str] = mapped_column(String(20), nullable=False)
    character_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    choice_options: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    child_choice: Mapped[str | None] = mapped_column(Text, nullable=True)
    bgm_scene: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session: Mapped["StorySessionModel"] = relationship("StorySessionModel", back_populates="turns")


class StoryGeneratedContentModel(Base):
    """AI-generated content (song, Q&A, interactive choices) for a story session."""

    __tablename__ = "story_generated_content"
    __table_args__ = (
        Index("idx_story_content_session", "session_id"),
        Index("idx_story_content_type", "session_id", "content_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}", default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session: Mapped["StorySessionModel"] = relationship(
        "StorySessionModel", back_populates="generated_contents"
    )


class StoryCostEventModel(Base):
    """Cost tracking event for LLM, TTS, and image generation calls within a story session."""

    __tablename__ = "story_cost_events"
    __table_args__ = (
        Index("idx_story_cost_session", "session_id"),
        Index("idx_story_cost_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    characters_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_estimate: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), nullable=False, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session: Mapped["StorySessionModel"] = relationship(
        "StorySessionModel", back_populates="cost_events"
    )
