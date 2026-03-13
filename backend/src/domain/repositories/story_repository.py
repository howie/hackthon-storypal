"""StoryPal Repository Interface.

Feature: 017-storypal (Clean Architecture Sprint 2)
Abstract interface for all story persistence operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class IStoryRepository(ABC):
    """Abstract repository for StoryPal persistence operations.

    All methods return infrastructure-layer objects (ORM models) typed as Any
    so that the domain layer remains free of infrastructure imports.
    Route handlers and background tasks rely on duck-typed attribute access.
    """

    # -------------------------------------------------------------------------
    # Template operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def list_templates(
        self,
        category: str | None = None,
        language: str | None = None,
    ) -> list[Any]:
        """List story templates from the database with optional filters."""
        ...

    @abstractmethod
    async def get_template(self, template_id: UUID) -> Any | None:
        """Get a single story template by ID. Returns None if not found."""
        ...

    # -------------------------------------------------------------------------
    # Session operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def create_session(self, data: dict[str, Any]) -> Any:
        """Create a new story session and return the persisted model."""
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID, user_id: UUID) -> Any | None:
        """Get a session with ownership check. Returns None if not found/not owned."""
        ...

    @abstractmethod
    async def get_session_with_turns(
        self,
        session_id: UUID,
        user_id: UUID | None = None,
    ) -> Any | None:
        """Get a session with eagerly-loaded turns.

        If user_id is provided, adds ownership check.
        Returns None if not found.
        """
        ...

    @abstractmethod
    async def list_sessions(
        self,
        user_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        """List sessions for a user with optional status filter.

        Returns (sessions, total_count).
        """
        ...

    @abstractmethod
    async def update_session(
        self,
        session_id: UUID,
        user_id: UUID,
        updates: dict[str, Any],
    ) -> Any:
        """Update specific fields on a session (ownership-checked).

        Returns the updated model.
        """
        ...

    @abstractmethod
    async def update_session_state(
        self,
        session_id: UUID,
        state_updates: dict[str, Any],
    ) -> None:
        """Merge state_updates into a session's story_state JSONB field."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        """Delete a session and its associated turns/content (ownership-checked)."""
        ...

    @abstractmethod
    async def set_session_generating(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Atomically set generation_status to 'generating' if not already generating.

        Returns True if the status was successfully set (caller should launch task).
        Returns False if already generating (no-op).
        """
        ...

    @abstractmethod
    async def set_session_synthesizing(
        self,
        session_id: UUID,
        user_id: UUID,
        total_turns: int,
    ) -> bool:
        """Atomically set synthesis_status to 'synthesizing' if not already synthesizing.

        Also initialises synthesis_progress to {completed: 0, total: total_turns}.
        Returns True if the status was successfully set (caller should launch task).
        Returns False if already synthesizing (no-op).
        """
        ...

    @abstractmethod
    async def set_session_image_generating(
        self,
        session_id: UUID,
        user_id: UUID,
        total_images: int,
    ) -> bool:
        """Atomically set image_generation_status to 'generating' if not already.

        Also initialises image_generation_progress to {completed: 0, total: total_images}.
        Returns True if the status was successfully set (caller should launch task).
        Returns False if already generating (no-op).
        """
        ...

    @abstractmethod
    async def update_image_generation_progress(
        self,
        session_id: UUID,
        completed: int,
        total: int,
    ) -> None:
        """Update image generation progress in story_state JSONB."""
        ...

    # -------------------------------------------------------------------------
    # Turn operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def add_turn(self, data: dict[str, Any]) -> None:
        """Append a single turn to a session (fire-and-forget).

        Unlike create_turns which replaces all turns, this method adds one turn
        without touching existing turns. Used by WebSocket handlers for
        incremental turn persistence.

        The dict must include: session_id, turn_number, turn_type, content.
        Optional keys: character_name, bgm_scene, child_choice.
        """
        ...

    @abstractmethod
    async def create_turns(
        self,
        session_id: UUID,
        turns_data: list[dict[str, Any]],
    ) -> None:
        """Replace all turns for a session with new ones.

        Deletes existing turns for the session, then inserts new ones.
        Each dict in turns_data must have: turn_number, turn_type,
        character_name (optional), content, bgm_scene (optional).
        """
        ...

    @abstractmethod
    async def get_turn(self, turn_id: UUID, session_id: UUID) -> Any | None:
        """Get a single turn by ID and session_id. Returns None if not found."""
        ...

    @abstractmethod
    async def update_turn_content(
        self,
        turn_id: UUID,
        session_id: UUID,
        content: str,
    ) -> tuple[Any | None, list[str]]:
        """Update the text content of a turn, clearing stale audio/image paths.

        Returns (updated_model, stale_storage_paths).
        The caller is responsible for deleting stale files from storage.
        Returns (None, []) if the turn is not found.
        """
        ...

    @abstractmethod
    async def update_turn_audio(self, turn_id: UUID, audio_path: str) -> None:
        """Update the audio_path field of a turn."""
        ...

    @abstractmethod
    async def update_turn_image(
        self, turn_id: UUID, image_path: str, scene_description: str
    ) -> None:
        """Update the image_path and scene_description fields of a turn."""
        ...

    @abstractmethod
    async def get_turns_for_session(self, session_id: UUID) -> list[Any]:
        """Return all turns for a session ordered by turn_number."""
        ...

    # -------------------------------------------------------------------------
    # Generated content operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def create_generated_content(self, data: dict[str, Any]) -> Any:
        """Create a StoryGeneratedContent record and return the persisted model."""
        ...

    @abstractmethod
    async def list_generated_content(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> list[Any]:
        """List generated content for a session (ownership-checked)."""
        ...

    # -------------------------------------------------------------------------
    # Cost event operations
    # -------------------------------------------------------------------------

    @abstractmethod
    async def create_cost_event(self, data: dict[str, Any]) -> None:
        """Persist a single cost tracking event (best-effort)."""
        ...
