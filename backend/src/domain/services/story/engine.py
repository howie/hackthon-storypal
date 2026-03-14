"""Core StoryPal story engine service.

LLM-driven interactive story engine that generates branching
narratives for children with structured JSON output.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from src.application.interfaces.llm_provider import ILLMProvider, LLMMessage, LLMResponse
from src.domain.entities.story import (
    ImagePromptItem,
    SceneInfo,
    StoryBranch,
    StorySession,
    StoryTemplate,
    StoryTurnType,
)
from src.domain.services.story.prompts import (
    IMAGE_PROMPT_SYSTEM_PROMPT,
    get_branching_story_system_prompt,
    get_complete_story_system_prompt,
    get_complete_story_user_prompt,
    get_story_choice_prompt,
    get_story_continuation_context,
    get_story_opening_prompt,
    get_story_question_response_context,
    get_story_system_prompt_template,
)

logger = logging.getLogger(__name__)

CostCallback = Callable[[str, LLMResponse], Awaitable[None]]


def _language_display_name(code: str) -> str:
    """Map language code to display name for LLM prompts."""
    return "English" if code.lower().startswith("en") else "繁體中文"


@dataclass
class StorySegment:
    """A parsed segment from LLM story response."""

    type: StoryTurnType
    content: str
    character_name: str | None = None
    emotion: str = "neutral"
    scene: str | None = None
    choice_options: list[str] | None = None


@dataclass
class StoryResponse:
    """Full parsed response from story LLM call."""

    segments: list[StorySegment] = field(default_factory=list)
    scene_change: SceneInfo | None = None
    story_summary: str = ""
    is_complete: bool = False


class StoryEngine:
    """LLM-driven interactive story engine."""

    def __init__(
        self,
        llm_provider: ILLMProvider,
        *,
        cost_callback: CostCallback | None = None,
    ) -> None:
        self._llm = llm_provider
        self._on_cost = cost_callback

    async def start_story(
        self,
        template: StoryTemplate,
        language: str = "zh-TW",
    ) -> tuple[list[StorySegment], SceneInfo | None, bool]:
        """Generate opening story segments from template.

        Args:
            template: Story template with characters, scenes, and prompts.
            language: Language code for the story (e.g. "zh-TW", "en").

        Returns:
            Tuple of (story segments, optional scene info, is_complete).
        """
        system_prompt = self._build_system_prompt(template, language=language)
        user_prompt = get_story_opening_prompt(language).format(
            language=_language_display_name(language),
        )

        logger.debug(
            "[StoryEngine][start_story] system_prompt=\n%s\nuser_prompt=\n%s",
            system_prompt,
            user_prompt,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self._call_llm(messages)
        parsed = self._parse_story_response(response)
        return parsed.segments, parsed.scene_change, parsed.is_complete

    async def generate_complete_story(
        self,
        template: StoryTemplate,
        language: str = "zh-TW",
        *,
        include_choice_points: bool = False,
    ) -> list[StorySegment]:
        """Generate a complete story from template.

        Unlike start_story(), this generates the full story in one shot.
        When *include_choice_points* is False (default), choice_prompt
        segments are stripped — suitable for the static playback mode.
        When True, choice_prompt segments with choice_options are kept —
        suitable for the branching (Dora-style) playback mode.

        Args:
            template: Story template with characters, scenes, and prompts.
            language: Language code for the story (e.g. "zh-TW", "en").
            include_choice_points: Keep choice_prompt segments if True.

        Returns:
            List of story segments.
        """
        characters_info = self._format_characters(template.characters)
        story_context = template.system_prompt or template.description

        base_prompt = (
            get_branching_story_system_prompt(language)
            if include_choice_points
            else get_complete_story_system_prompt(language)
        )
        section_label = "Story Setting" if language.startswith("en") else "故事設定"
        chars_label = "Characters" if language.startswith("en") else "角色列表"
        system_prompt = (
            base_prompt
            + f"\n\n## {section_label}\n{story_context}\n\n## {chars_label}\n{characters_info}"
        )
        user_prompt = get_complete_story_user_prompt(language).format(
            language=_language_display_name(language),
        )

        logger.debug(
            "[StoryEngine][generate_complete_story] system_prompt=\n%s\nuser_prompt=\n%s",
            system_prompt,
            user_prompt,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self._llm.generate(
            messages=messages,
            max_tokens=3000,
            temperature=0.8,
            response_format="json",
        )
        if self._on_cost:
            await self._on_cost("llm", response)
        parsed = self._parse_story_response(response.content)

        # Filter out choice_prompt segments unless branching mode is enabled
        if include_choice_points:
            return parsed.segments
        return [s for s in parsed.segments if s.type != StoryTurnType.CHOICE_PROMPT]

    async def continue_story(
        self,
        session: StorySession,
        child_input: str,
    ) -> tuple[list[StorySegment], SceneInfo | None, bool]:
        """Continue story based on child's choice or response.

        Args:
            session: Current story session with history.
            child_input: Child's text input (choice or free response).

        Returns:
            Tuple of (story segments, optional scene change, is_complete).
        """
        story_summary = session.story_state.get("summary", "故事剛開始")
        current_scene = session.current_scene or "未知場景"

        # Separate story context from user-controlled content (prompt injection defence)
        context_prompt = get_story_continuation_context(session.language).format(
            story_summary=story_summary,
            current_scene=current_scene,
        )

        logger.debug(
            "[StoryEngine][continue_story] context_prompt=\n%s\nchild_input=%r",
            context_prompt,
            child_input,
        )

        messages = self._build_conversation_messages(session, context_prompt)
        messages.append(LLMMessage(role="user", content=child_input))
        response = await self._call_llm(messages)
        parsed = self._parse_story_response(response)
        return parsed.segments, parsed.scene_change, parsed.is_complete

    async def handle_question(
        self,
        session: StorySession,
        question: str,
    ) -> tuple[list[StorySegment], SceneInfo | None, bool]:
        """Handle child's off-topic question, then return to story.

        Args:
            session: Current story session.
            question: Child's question text.

        Returns:
            Tuple of (response segments, optional scene change, is_complete).
        """
        story_summary = session.story_state.get("summary", "故事剛開始")
        characters_info = self._format_characters(session.characters_config)

        # Separate story context from user-controlled content (prompt injection defence)
        context_prompt = get_story_question_response_context(session.language).format(
            story_summary=story_summary,
            characters_info=characters_info,
        )

        logger.debug(
            "[StoryEngine][handle_question] context_prompt=\n%s\nquestion=%r",
            context_prompt,
            question,
        )

        messages = self._build_conversation_messages(session, context_prompt)
        messages.append(LLMMessage(role="user", content=question))
        response = await self._call_llm(messages)
        parsed = self._parse_story_response(response)
        return parsed.segments, parsed.scene_change, parsed.is_complete

    async def generate_choice(
        self,
        session: StorySession,
    ) -> StoryBranch:
        """Generate a decision point for the child.

        Args:
            session: Current story session.

        Returns:
            StoryBranch with prompt and options.
        """
        story_summary = session.story_state.get("summary", "故事剛開始")
        current_scene = session.current_scene or "未知場景"

        user_prompt = get_story_choice_prompt(session.language).format(
            story_summary=story_summary,
            current_scene=current_scene,
        )

        messages = self._build_conversation_messages(session, user_prompt)
        response = await self._call_llm(messages)
        parsed = self._parse_story_response(response)

        # Extract choice from the last choice_prompt segment
        options: list[str] = []
        prompt_text = ""
        for seg in parsed.segments:
            if seg.type == StoryTurnType.CHOICE_PROMPT:
                prompt_text = seg.content
                # Parse numbered options from content
                lines = seg.content.split("\n")
                for line in lines:
                    match = re.match(r"^\d+[.、]\s*(.+)$", line.strip())
                    if match:
                        options.append(match.group(1))

        return StoryBranch(
            prompt_text=prompt_text,
            options=options,
            context=parsed.story_summary,
        )

    async def generate_image_prompts(
        self,
        turns: list[Any],
    ) -> list[ImagePromptItem]:
        """Analyse story turns and generate pixel art image prompts.

        Args:
            turns: List of story turns (ORM models or domain entities).

        Returns:
            List of ImagePromptItem with turn_number, image_prompt, scene_description.
        """
        # Build story text from turns
        story_text_parts = []
        for t in turns:
            turn_number = t.turn_number if hasattr(t, "turn_number") else 0
            content = t.content if hasattr(t, "content") else str(t)
            char_name = getattr(t, "character_name", None)
            prefix = f"[{char_name}]" if char_name else "[旁白]"
            story_text_parts.append(f"段落 {turn_number}: {prefix} {content}")

        story_text = "\n".join(story_text_parts)

        messages = [
            LLMMessage(role="system", content=IMAGE_PROMPT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=f"以下是完整故事文字：\n\n{story_text}"),
        ]

        response = await self._llm.generate(
            messages=messages,
            max_tokens=2000,
            temperature=0.4,
            response_format="json",
        )
        if self._on_cost:
            await self._on_cost("llm", response)

        # Parse JSON response — reuse 3-stage extraction
        text = response.content.strip()
        data = None

        # Stage 1: direct parse
        with contextlib.suppress(json.JSONDecodeError):
            data = json.loads(text)

        # Stage 2: markdown fence
        if data is None:
            fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
            if fence_match:
                with contextlib.suppress(json.JSONDecodeError):
                    data = json.loads(fence_match.group(1).strip())

        # Stage 3: bracket extraction
        if data is None:
            bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
            if bracket_match:
                with contextlib.suppress(json.JSONDecodeError):
                    data = json.loads(bracket_match.group(0))

        if data is None:
            logger.error("[StoryEngine] Failed to parse image prompt JSON: %r", text[:200])
            raise ValueError("Failed to parse image prompt response as JSON")

        # Handle both list and dict with "prompts" key
        items_data = data if isinstance(data, list) else data.get("prompts", data.get("images", []))

        result = []
        for item in items_data:
            if not isinstance(item, dict):
                continue
            result.append(
                ImagePromptItem(
                    turn_number=item.get("turn_number", 0),
                    image_prompt=item.get("image_prompt", ""),
                    scene_description=item.get("scene_description", ""),
                )
            )

        if not result:
            logger.warning("[StoryEngine] LLM returned 0 image prompts")

        return result

    def _build_system_prompt(self, template: StoryTemplate, *, language: str = "zh-TW") -> str:
        """Build the system prompt from template."""
        characters_info = self._format_characters(template.characters)
        story_context = template.system_prompt or template.description

        return get_story_system_prompt_template(language).format(
            age_min=template.target_age_min,
            age_max=template.target_age_max,
            story_context=story_context,
            characters_info=characters_info,
        )

    def _build_conversation_messages(
        self,
        session: StorySession,
        user_prompt: str,
    ) -> list[LLMMessage]:
        """Build conversation history context for LLM.

        Constructs a message list from the session's system prompt
        and recent turn history.
        """
        messages: list[LLMMessage] = []

        # Add system prompt from story state
        system_prompt = session.story_state.get("system_prompt", "")
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))

        # Add recent turns as conversation history (last 20 turns max)
        recent_turns = session.turns[-20:]
        for turn in recent_turns:
            if turn.turn_type in (
                StoryTurnType.CHILD_RESPONSE,
                StoryTurnType.QUESTION,
            ):
                messages.append(LLMMessage(role="user", content=turn.content))
            elif turn.turn_type in (
                StoryTurnType.NARRATION,
                StoryTurnType.DIALOGUE,
                StoryTurnType.CHOICE_PROMPT,
                StoryTurnType.ANSWER,
            ):
                messages.append(LLMMessage(role="assistant", content=turn.content))

        # Add current user prompt
        messages.append(LLMMessage(role="user", content=user_prompt))
        return messages

    def _format_characters(
        self,
        characters: list[Any],
    ) -> str:
        """Format character list for prompt insertion."""
        if not characters:
            return "無指定角色"

        lines = []
        for char in characters:
            line = f"- {char.name}：{char.description}"
            if char.emotion != "neutral":
                line += f"（目前情緒：{char.emotion}）"
            lines.append(line)
        return "\n".join(lines)

    async def _call_llm(self, messages: list[LLMMessage], *, timeout: float = 30.0) -> str:
        """Call LLM and return raw response content.

        Args:
            messages: Conversation messages for the LLM.
            timeout: Maximum seconds to wait for LLM response.

        Raises:
            asyncio.TimeoutError: If the LLM call exceeds *timeout* seconds.
        """
        response = await asyncio.wait_for(
            self._llm.generate(
                messages=messages,
                max_tokens=1500,
                temperature=0.8,
                response_format="json",
            ),
            timeout=timeout,
        )
        if self._on_cost:
            await self._on_cost("llm", response)
        return response.content

    def _parse_story_response(self, llm_response: str) -> StoryResponse:
        """Parse LLM JSON response into StoryResponse.

        Attempts JSON extraction in three stages (BE-B#3):
        1. Direct json.loads on the raw (stripped) response.
        2. Strip markdown fences (```json ... ```) then json.loads.
        3. Regex extraction of the outermost ``{...}`` block then json.loads.
        Raises ValueError if all three stages fail so the caller can handle
        the error explicitly instead of silently falling back to raw text.
        """
        text = llm_response.strip()

        # Stage 1: direct parse
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Stage 2: strip markdown fences
            fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
            if fence_match:
                try:
                    data = json.loads(fence_match.group(1).strip())
                except json.JSONDecodeError:
                    data = None
            else:
                data = None

        if data is None:
            # Stage 3: extract outermost {...} block via regex
            brace_match = re.search(r"\{.*\}", text, re.DOTALL)
            if brace_match:
                try:
                    data = json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    data = None

        if data is None:
            logger.error(
                "[StoryEngine] All JSON parse stages failed for LLM response (first 200 chars): %r",
                text[:200],
            )
            raise ValueError(
                "LLM returned a response that could not be parsed as JSON. "
                "Check logs for the raw response."
            )

        # Parse segments
        segments: list[StorySegment] = []
        for seg_data in data.get("segments", []):
            turn_type = self._map_segment_type(seg_data.get("type", "narration"))
            segments.append(
                StorySegment(
                    type=turn_type,
                    content=seg_data.get("content", ""),
                    character_name=seg_data.get("character_name"),
                    emotion=seg_data.get("emotion", "neutral"),
                    scene=seg_data.get("scene"),
                    choice_options=seg_data.get("choice_options"),
                )
            )

        # Parse scene change
        scene_change = None
        sc_data = data.get("scene_change")
        if sc_data:
            scene_change = SceneInfo(
                name=sc_data.get("name", ""),
                description=sc_data.get("description", ""),
                bgm_prompt=sc_data.get("bgm_prompt", ""),
                mood=sc_data.get("mood", "neutral"),
            )

        return StoryResponse(
            segments=segments,
            scene_change=scene_change,
            story_summary=data.get("story_summary", ""),
            is_complete=bool(data.get("is_complete", False)),
        )

    @staticmethod
    def _map_segment_type(type_str: str) -> StoryTurnType:
        """Map string type to StoryTurnType enum."""
        mapping = {
            "narration": StoryTurnType.NARRATION,
            "dialogue": StoryTurnType.DIALOGUE,
            "choice_prompt": StoryTurnType.CHOICE_PROMPT,
            "child_response": StoryTurnType.CHILD_RESPONSE,
            "question": StoryTurnType.QUESTION,
            "answer": StoryTurnType.ANSWER,
        }
        return mapping.get(type_str, StoryTurnType.NARRATION)
