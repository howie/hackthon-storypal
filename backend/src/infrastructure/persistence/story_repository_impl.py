"""StoryPal Repository Implementation.

Feature: 017-storypal (Clean Architecture Sprint 2)
SQLAlchemy implementation of IStoryRepository.
All ORM operations are encapsulated here; no ORM code appears in routes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.story import StorySessionStatus
from src.domain.repositories.story_repository import IStoryRepository
from src.infrastructure.persistence.models import (
    StoryCostEventModel,
    StoryGeneratedContentModel,
    StorySessionModel,
    StoryTemplateModel,
    StoryTurnModel,
)


class StoryRepositoryImpl(IStoryRepository):
    """SQLAlchemy implementation of IStoryRepository.

    Commit strategy: each mutation method commits after the operation so
    that route handlers and background tasks do not need to manage commits
    explicitly.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Template operations
    # -------------------------------------------------------------------------

    async def list_templates(
        self,
        category: str | None = None,
        language: str | None = None,
    ) -> list[Any]:
        stmt = select(StoryTemplateModel)
        if category:
            stmt = stmt.where(StoryTemplateModel.category == category)
        if language:
            stmt = stmt.where(StoryTemplateModel.language == language)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_template(self, template_id: uuid.UUID) -> Any | None:
        result = await self._db.execute(
            select(StoryTemplateModel).where(StoryTemplateModel.id == template_id)
        )
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Session operations
    # -------------------------------------------------------------------------

    async def create_session(self, data: dict[str, Any]) -> Any:
        db_session = StorySessionModel(
            id=data.get("id", uuid.uuid4()),
            user_id=data["user_id"],
            template_id=data.get("template_id"),
            title=data["title"],
            language=data["language"],
            status=data["status"],
            story_state=data.get("story_state", {}),
            characters_config=data.get("characters_config", []),
            child_config=data.get("child_config", {}),
            started_at=data.get("started_at", datetime.now(UTC)),
        )
        self._db.add(db_session)
        await self._db.commit()
        await self._db.refresh(db_session)
        return db_session

    async def get_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> Any | None:
        result = await self._db.execute(
            select(StorySessionModel).where(
                StorySessionModel.id == session_id,
                StorySessionModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_session_with_turns(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Any | None:
        stmt = select(StorySessionModel).where(StorySessionModel.id == session_id)
        if user_id is not None:
            stmt = stmt.where(StorySessionModel.user_id == user_id)
        stmt = stmt.options(selectinload(StorySessionModel.turns))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        stmt = select(StorySessionModel).where(StorySessionModel.user_id == user_id)
        if status:
            stmt = stmt.where(StorySessionModel.status == status)
        stmt = stmt.order_by(StorySessionModel.updated_at.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> Any:
        result = await self._db.execute(
            select(StorySessionModel)
            .where(
                StorySessionModel.id == session_id,
                StorySessionModel.user_id == user_id,
            )
            .options(selectinload(StorySessionModel.turns))
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return None
        for key, value in updates.items():
            setattr(db_session, key, value)
        await self._db.commit()
        await self._db.refresh(db_session)
        return db_session

    async def update_session_state(
        self,
        session_id: uuid.UUID,
        state_updates: dict[str, Any],
    ) -> None:
        result = await self._db.execute(
            select(StorySessionModel).where(StorySessionModel.id == session_id)
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return

        # Route dedicated status/error fields to their own columns (BE-C#2).
        # Remaining keys (e.g. synthesis_progress, system_prompt) go to JSONB.
        _status_columns = {
            "generation_status",
            "synthesis_status",
            "generation_error",
            "synthesis_error",
            "image_generation_status",
            "image_generation_error",
        }
        jsonb_updates = {}
        for key, value in state_updates.items():
            if key in _status_columns:
                setattr(db_session, key, value)
            else:
                jsonb_updates[key] = value

        if jsonb_updates:
            state = dict(db_session.story_state or {})
            state.update(jsonb_updates)
            db_session.story_state = state

        db_session.updated_at = datetime.now(UTC)
        # Increment version for optimistic locking (BE-C#5)
        db_session.version = (db_session.version or 0) + 1
        await self._db.commit()

    async def delete_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
        result = await self._db.execute(
            select(StorySessionModel).where(
                StorySessionModel.id == session_id,
                StorySessionModel.user_id == user_id,
            )
        )
        db_session = result.scalar_one_or_none()
        if db_session:
            await self._db.delete(db_session)
            await self._db.commit()

    async def set_session_generating(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Atomically set generation_status='generating' if not already generating.

        Uses PostgreSQL UPDATE … WHERE … RETURNING for true atomicity,
        preventing race conditions when multiple concurrent requests target
        the same session.
        """
        stmt = text("""
            UPDATE story_sessions
            SET generation_status = 'generating',
                generation_error  = NULL
            WHERE id = :session_id
              AND user_id = :user_id
              AND (generation_status IS DISTINCT FROM 'generating')
            RETURNING id
        """)
        result = await self._db.execute(stmt, {"session_id": session_id, "user_id": user_id})
        success = result.scalar_one_or_none() is not None
        if success:
            await self._db.commit()
        return success

    async def set_session_synthesizing(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        total_turns: int,
    ) -> bool:
        """Atomically set synthesis_status='synthesizing' if not already synthesizing.

        Uses PostgreSQL UPDATE … WHERE … RETURNING for true atomicity,
        preventing race conditions when multiple concurrent requests target
        the same session.
        """
        stmt = text("""
            UPDATE story_sessions
            SET synthesis_status = 'synthesizing',
                synthesis_error  = NULL,
                story_state = story_state
                    || jsonb_build_object(
                        'synthesis_progress', jsonb_build_object('completed', 0, 'total', CAST(:total AS integer))
                    )
            WHERE id = :session_id
              AND user_id = :user_id
              AND (synthesis_status IS DISTINCT FROM 'synthesizing')
            RETURNING id
        """)
        result = await self._db.execute(
            stmt,
            {"session_id": session_id, "user_id": user_id, "total": total_turns},
        )
        success = result.scalar_one_or_none() is not None
        if success:
            await self._db.commit()
        return success

    async def set_session_image_generating(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        total_images: int,
    ) -> bool:
        """Atomically set image_generation_status='generating' if not already."""
        stmt = text("""
            UPDATE story_sessions
            SET image_generation_status = 'generating',
                image_generation_error  = NULL,
                story_state = story_state
                    || jsonb_build_object(
                        'image_generation_progress', jsonb_build_object('completed', 0, 'total', CAST(:total AS integer))
                    )
            WHERE id = :session_id
              AND user_id = :user_id
              AND (image_generation_status IS DISTINCT FROM 'generating')
            RETURNING id
        """)
        result = await self._db.execute(
            stmt,
            {"session_id": session_id, "user_id": user_id, "total": total_images},
        )
        success = result.scalar_one_or_none() is not None
        if success:
            await self._db.commit()
        return success

    async def update_image_generation_progress(
        self,
        session_id: uuid.UUID,
        completed: int,
        total: int,
    ) -> None:
        result = await self._db.execute(
            select(StorySessionModel).where(StorySessionModel.id == session_id)
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return
        state = dict(db_session.story_state or {})
        state["image_generation_progress"] = {"completed": completed, "total": total}
        db_session.story_state = state
        db_session.version = (db_session.version or 0) + 1
        await self._db.commit()

    # -------------------------------------------------------------------------
    # Turn operations
    # -------------------------------------------------------------------------

    async def add_turn(self, data: dict[str, Any]) -> None:
        turn = StoryTurnModel(
            id=data.get("id", uuid.uuid4()),
            session_id=data["session_id"],
            turn_number=data["turn_number"],
            turn_type=data["turn_type"],
            content=data["content"],
            character_name=data.get("character_name"),
            bgm_scene=data.get("bgm_scene"),
            child_choice=data.get("child_choice"),
        )
        self._db.add(turn)
        await self._db.commit()

    async def create_turns(
        self,
        session_id: uuid.UUID,
        turns_data: list[dict[str, Any]],
    ) -> None:
        """Replace all turns for a session with turns_data entries."""
        # Load existing turns
        result = await self._db.execute(
            select(StorySessionModel)
            .where(StorySessionModel.id == session_id)
            .options(selectinload(StorySessionModel.turns))
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return

        # Delete existing turns
        for existing_turn in list(db_session.turns or []):
            await self._db.delete(existing_turn)
        await self._db.flush()

        # Insert new turns
        for td in turns_data:
            turn = StoryTurnModel(
                id=td.get("id", uuid.uuid4()),
                session_id=session_id,
                turn_number=td["turn_number"],
                turn_type=td["turn_type"],
                character_name=td.get("character_name"),
                content=td["content"],
                bgm_scene=td.get("bgm_scene"),
                choice_options=td.get("choice_options"),
            )
            self._db.add(turn)

        # Update generation status via dedicated columns (BE-C#2)
        db_session.generation_status = "completed"
        db_session.generation_error = None
        db_session.updated_at = datetime.now(UTC)
        await self._db.commit()

    async def get_turn(self, turn_id: uuid.UUID, session_id: uuid.UUID) -> Any | None:
        result = await self._db.execute(
            select(StoryTurnModel).where(
                StoryTurnModel.id == turn_id,
                StoryTurnModel.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_turn_content(
        self,
        turn_id: uuid.UUID,
        session_id: uuid.UUID,
        content: str,
    ) -> tuple[Any | None, list[str]]:
        result = await self._db.execute(
            select(StoryTurnModel).where(
                StoryTurnModel.id == turn_id,
                StoryTurnModel.session_id == session_id,
            )
        )
        turn = result.scalar_one_or_none()
        if not turn:
            return None, []

        # Capture stale paths atomically before clearing
        stale_paths = [p for p in (turn.audio_path, getattr(turn, "image_path", None)) if p]

        turn.content = content
        turn.audio_path = None
        turn.image_path = None
        turn.scene_description = None
        await self._db.commit()
        await self._db.refresh(turn)
        return turn, stale_paths

    async def update_turn_image(
        self, turn_id: uuid.UUID, image_path: str, scene_description: str
    ) -> None:
        result = await self._db.execute(select(StoryTurnModel).where(StoryTurnModel.id == turn_id))
        turn = result.scalar_one_or_none()
        if turn:
            turn.image_path = image_path
            turn.scene_description = scene_description
            await self._db.commit()

    async def update_turn_audio(self, turn_id: uuid.UUID, audio_path: str) -> None:
        result = await self._db.execute(select(StoryTurnModel).where(StoryTurnModel.id == turn_id))
        turn = result.scalar_one_or_none()
        if turn:
            turn.audio_path = audio_path
            await self._db.commit()

    async def count_completed_sessions(self, user_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                StorySessionModel.user_id == user_id,
                StorySessionModel.status == StorySessionStatus.COMPLETED,
            )
        )
        return result.scalar_one()

    async def get_turns_for_session(self, session_id: uuid.UUID) -> list[Any]:
        result = await self._db.execute(
            select(StoryTurnModel)
            .where(StoryTurnModel.session_id == session_id)
            .order_by(StoryTurnModel.turn_number)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Generated content operations
    # -------------------------------------------------------------------------

    async def create_generated_content(self, data: dict[str, Any]) -> Any:
        db_content = StoryGeneratedContentModel(
            id=data.get("id", uuid.uuid4()),
            session_id=data["session_id"],
            content_type=data["content_type"],
            content_data=data["content_data"],
        )
        self._db.add(db_content)
        await self._db.commit()
        await self._db.refresh(db_content)
        return db_content

    async def list_generated_content(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Any]:
        # Verify ownership first
        sess = await self.get_session(session_id, user_id)
        if not sess:
            return []
        result = await self._db.execute(
            select(StoryGeneratedContentModel)
            .where(StoryGeneratedContentModel.session_id == session_id)
            .order_by(StoryGeneratedContentModel.created_at)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Cost event operations
    # -------------------------------------------------------------------------

    async def create_cost_event(self, data: dict[str, Any]) -> None:
        event = StoryCostEventModel(**data)
        self._db.add(event)
        await self._db.commit()
