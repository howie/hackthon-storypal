"""StoryPal content generator — song, Q&A, interactive choices.

Generates supplemental content for a completed or active story session
using the configured LLM provider.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from src.application.interfaces.llm_provider import ILLMProvider, LLMMessage
from src.domain.entities.story import (
    ChildConfig,
    GeneratedContentType,
    StoryGeneratedContent,
    StorySession,
    StoryTurnType,
)
from src.domain.services.story.prompts import (
    INTERACTIVE_CHOICES_SYSTEM_PROMPT,
    INTERACTIVE_CHOICES_USER_PROMPT_TEMPLATE,
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT_TEMPLATE,
    SONG_SYSTEM_PROMPT,
    SONG_USER_PROMPT_TEMPLATE,
    VALUE_LABELS,
)

logger = logging.getLogger(__name__)


class StoryContentGenerator:
    """Generates supplemental content for story sessions via LLM."""

    def __init__(self, llm_provider: ILLMProvider) -> None:
        self._llm = llm_provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_song(self, session: StorySession) -> StoryGeneratedContent:
        """Generate a children's song (lyrics + Suno prompt) for *session*."""
        child = self._child_config(session)
        values = self._values_text(child)

        user_prompt = SONG_USER_PROMPT_TEMPLATE.format(
            age=child.age,
            character=child.favorite_character or "故事主角",
            learning_goals=child.learning_goals or "基本生活技能",
            values=values,
        )

        logger.debug(
            "[ContentGenerator][song][age=%s] prompt=\n%s",
            child.age,
            user_prompt,
        )

        raw = await self._call_llm(
            system=SONG_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1500,
            response_format="json",
        )
        data = self._parse_json(raw)
        data["generated_at"] = datetime.now(tz=UTC).isoformat()

        return StoryGeneratedContent(
            session_id=session.id,
            content_type=GeneratedContentType.SONG,
            content_data=data,
        )

    async def generate_qa(self, session: StorySession) -> StoryGeneratedContent:
        """Generate Q&A questions for *session*."""
        child = self._child_config(session)
        story_summary = self._story_summary(session)

        user_prompt = QA_USER_PROMPT_TEMPLATE.format(
            age=child.age,
            character=child.favorite_character or "故事主角",
            learning_goals=child.learning_goals or "基本生活技能",
            story_summary=story_summary,
        )

        logger.debug(
            "[ContentGenerator][qa][age=%s] prompt=\n%s",
            child.age,
            user_prompt,
        )

        raw = await self._call_llm(
            system=QA_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=4000,
            response_format="json",
        )
        data = self._parse_json(raw)
        data["generated_at"] = datetime.now(tz=UTC).isoformat()

        return StoryGeneratedContent(
            session_id=session.id,
            content_type=GeneratedContentType.QA,
            content_data=data,
        )

    async def generate_interactive_choices(self, session: StorySession) -> StoryGeneratedContent:
        """Generate interactive choice nodes for *session*."""
        child = self._child_config(session)
        story_summary = self._story_summary(session)

        user_prompt = INTERACTIVE_CHOICES_USER_PROMPT_TEMPLATE.format(
            age=child.age,
            character=child.favorite_character or "故事主角",
            learning_goals=child.learning_goals or "基本生活技能",
            story_summary=story_summary,
        )

        logger.debug(
            "[ContentGenerator][interactive_choices][age=%s] prompt=\n%s",
            child.age,
            user_prompt,
        )

        raw = await self._call_llm(
            system=INTERACTIVE_CHOICES_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=2500,
            response_format="json",
        )
        data = self._parse_json(raw)
        data["generated_at"] = datetime.now(tz=UTC).isoformat()

        return StoryGeneratedContent(
            session_id=session.id,
            content_type=GeneratedContentType.INTERACTIVE_CHOICES,
            content_data=data,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _child_config(session: StorySession) -> ChildConfig:
        return session.child_config

    @staticmethod
    def _values_text(child: ChildConfig) -> str:
        return "、".join(VALUE_LABELS.get(v, v) for v in child.selected_values) or "由故事決定"

    @staticmethod
    def _story_summary(session: StorySession) -> str:
        """Build a concise story summary from recent turns."""
        narration_turns = [
            t
            for t in session.turns
            if t.turn_type in (StoryTurnType.NARRATION, StoryTurnType.DIALOGUE)
        ]
        if not narration_turns:
            return session.story_state.get("summary", "故事尚未開始")
        # Take the last few turns as summary context
        recent = narration_turns[-6:]
        return "\n".join(t.content for t in recent)

    async def _call_llm(
        self,
        system: str,
        user: str,
        max_tokens: int = 1500,
        response_format: str | None = None,
    ) -> str:
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]
        response = await self._llm.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.8,
            response_format=response_format,
        )
        return response.content

    @staticmethod
    def _parse_json(llm_response: str) -> dict[str, Any]:
        """Parse JSON from LLM response using a multi-stage extraction strategy (BE-B#3).

        Stages:
        1. Direct json.loads on the stripped response.
        2. Strip markdown fences (```json ... ```) then json.loads.
        3. Regex extraction of the outermost ``{...}`` block then json.loads.
        Raises ValueError on total failure so the caller can propagate the
        error rather than silently substituting a ``raw_text`` placeholder.
        """
        text = llm_response.strip()

        # Stage 1: direct parse
        try:
            result: dict[str, Any] = json.loads(text)
            return result
        except json.JSONDecodeError:
            pass

        # Stage 2: strip markdown fences
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if fence_match:
            try:
                result = json.loads(fence_match.group(1).strip())
                return result
            except json.JSONDecodeError:
                pass

        # Stage 3: extract outermost {...} block
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                result = json.loads(brace_match.group(0))
                return result
            except json.JSONDecodeError:
                pass

        logger.error(
            "[ContentGenerator] All JSON parse stages failed for LLM response "
            "(first 200 chars): %r",
            text[:200],
        )
        raise ValueError(
            "LLM returned a response that could not be parsed as JSON. "
            "Check logs for the raw response."
        )
