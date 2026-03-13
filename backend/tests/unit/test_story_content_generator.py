"""Unit tests for StoryContentGenerator.

Feature: 017-storypal — Phase 2
Task: T053 — Test generate_interactive_choices():
  - mock ILLMProvider
  - assert returns StoryGeneratedContent(content_type="interactive_choices")
  - content_data contains choice_nodes array, each node has options/timeout_hint

Task: T054 — Test generate_qa():
  - assert content_data contains questions array + closing string
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.application.interfaces.llm_provider import LLMResponse
from src.domain.entities.story import (
    ChildConfig,
    GeneratedContentType,
    StorySession,
    StoryTurn,
    StoryTurnType,
)
from src.domain.services.story.content_generator import StoryContentGenerator

# =============================================================================
# Fixtures
# =============================================================================


def _make_session(
    child_config: ChildConfig | None = None,
    turns: list[StoryTurn] | None = None,
) -> StorySession:
    """Create a minimal StorySession for testing."""
    return StorySession(
        title="測試故事",
        language="zh-TW",
        child_config=child_config
        or ChildConfig(
            age=5,
            learning_goals="自己穿室內拖",
            selected_values=["empathy_care"],
            selected_emotions=["pride"],
            favorite_character="超人力霸王",
        ),
        turns=turns or [],
    )


def _make_mock_llm(response_json: dict) -> AsyncMock:
    """Create a mock ILLMProvider that returns the given JSON."""
    mock = AsyncMock()
    mock.generate.return_value = LLMResponse(
        content=json.dumps(response_json, ensure_ascii=False),
        latency_ms=100,
        input_tokens=50,
        output_tokens=200,
    )
    return mock


# =============================================================================
# T053 — generate_interactive_choices
# =============================================================================


INTERACTIVE_CHOICES_RESPONSE = {
    "script": "超人力霸王在森林裡遇到了一個分岔路…",
    "choice_nodes": [
        {
            "order": 1,
            "prompt": "超人力霸王看到兩條路，你覺得他應該走哪一條？",
            "options": ["左邊的神祕小路", "右邊的陽光大道"],
            "timeout_seconds": 5,
            "timeout_hint": "如果你還沒想好，超人力霸王會先走左邊喔！",
        },
        {
            "order": 2,
            "prompt": "走著走著，超人力霸王遇到了一隻小兔子在哭，你要怎麼做？",
            "options": ["幫助小兔子", "繼續往前走"],
            "timeout_seconds": 5,
            "timeout_hint": "超人力霸王覺得應該幫幫小兔子呢！",
        },
    ],
}


@pytest.mark.asyncio
class TestGenerateInteractiveChoices:
    """T053 — generate_interactive_choices unit tests."""

    async def test_returns_story_generated_content(self) -> None:
        """Should return a StoryGeneratedContent instance."""
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        session = _make_session()

        result = await gen.generate_interactive_choices(session)

        assert result.session_id == session.id
        assert result.content_type == GeneratedContentType.INTERACTIVE_CHOICES

    async def test_content_type_is_interactive_choices(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        assert result.content_type == "interactive_choices"

    async def test_content_data_has_choice_nodes(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        assert "choice_nodes" in result.content_data
        assert isinstance(result.content_data["choice_nodes"], list)
        assert len(result.content_data["choice_nodes"]) >= 2

    async def test_choice_node_has_options(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        for node in result.content_data["choice_nodes"]:
            assert "options" in node
            assert isinstance(node["options"], list)
            assert len(node["options"]) >= 2

    async def test_choice_node_has_timeout_hint(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        for node in result.content_data["choice_nodes"]:
            assert "timeout_hint" in node
            assert isinstance(node["timeout_hint"], str)
            assert len(node["timeout_hint"]) > 0

    async def test_content_data_has_script(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        assert "script" in result.content_data
        assert isinstance(result.content_data["script"], str)

    async def test_content_data_has_generated_at(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        assert "generated_at" in result.content_data

    async def test_calls_llm_with_system_and_user_messages(self) -> None:
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_interactive_choices(_make_session())

        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    async def test_uses_story_turns_as_summary(self) -> None:
        """When session has narration turns, they should appear in user prompt."""
        turns = [
            StoryTurn(
                session_id=_make_session().id,
                turn_number=1,
                turn_type=StoryTurnType.NARRATION,
                content="超人力霸王來到了森林深處",
            ),
        ]
        session = _make_session(turns=turns)
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_interactive_choices(session)

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        user_content = messages[1].content
        assert "超人力霸王來到了森林深處" in user_content

    async def test_llm_returns_markdown_fenced_json(self) -> None:
        """Should handle LLM response wrapped in markdown code fences."""
        mock_llm = AsyncMock()
        fenced = f"```json\n{json.dumps(INTERACTIVE_CHOICES_RESPONSE, ensure_ascii=False)}\n```"
        mock_llm.generate.return_value = LLMResponse(
            content=fenced,
            latency_ms=100,
            input_tokens=50,
            output_tokens=200,
        )
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_interactive_choices(_make_session())
        assert "choice_nodes" in result.content_data

    async def test_passes_json_response_format(self) -> None:
        """Should pass response_format='json' to LLM provider."""
        mock_llm = _make_mock_llm(INTERACTIVE_CHOICES_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_interactive_choices(_make_session())

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["response_format"] == "json"


# =============================================================================
# T054 — generate_qa
# =============================================================================


QA_RESPONSE = {
    "questions": [
        {
            "order": 1,
            "question": "超人力霸王在森林裡遇到了誰？",
            "hint": "是一隻小動物喔！",
            "encouragement": "你好棒！觀察得很仔細！",
        },
        {
            "order": 2,
            "question": "小兔子為什麼在哭呢？",
            "hint": "想想看，小兔子是不是找不到什麼東西？",
            "encouragement": "答得真好！你很有同理心！",
        },
        {
            "order": 3,
            "question": "如果是你，你會怎麼幫助小兔子？",
            "hint": "可以想想生活中你怎麼幫助朋友的",
            "encouragement": "真是個好方法！你好有愛心！",
        },
    ],
    "closing": "今天的故事就到這裡啦，你表現得好棒！下次再一起冒險吧！",
    "timeout_seconds": 5,
}


@pytest.mark.asyncio
class TestGenerateQA:
    """T054 — generate_qa unit tests."""

    async def test_returns_story_generated_content(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        session = _make_session()
        result = await gen.generate_qa(session)
        assert result.session_id == session.id
        assert result.content_type == GeneratedContentType.QA

    async def test_content_type_is_qa(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_qa(_make_session())
        assert result.content_type == "qa"

    async def test_content_data_has_questions(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_qa(_make_session())
        assert "questions" in result.content_data
        assert isinstance(result.content_data["questions"], list)
        assert len(result.content_data["questions"]) >= 2

    async def test_question_has_required_fields(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_qa(_make_session())
        for q in result.content_data["questions"]:
            assert "question" in q
            assert "hint" in q
            assert "encouragement" in q
            assert "order" in q

    async def test_content_data_has_closing(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_qa(_make_session())
        assert "closing" in result.content_data
        assert isinstance(result.content_data["closing"], str)
        assert len(result.content_data["closing"]) > 0

    async def test_content_data_has_generated_at(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_qa(_make_session())
        assert "generated_at" in result.content_data

    async def test_calls_llm_with_correct_messages(self) -> None:
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_qa(_make_session())

        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    async def test_user_prompt_includes_child_info(self) -> None:
        """User prompt should include child's age, character, and learning goals."""
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_qa(_make_session())

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        user_content = messages[1].content
        assert "5" in user_content  # age
        assert "超人力霸王" in user_content  # character

    async def test_llm_returns_markdown_fenced_json(self) -> None:
        """Should handle LLM response wrapped in markdown code fences."""
        mock_llm = AsyncMock()
        fenced = f"```json\n{json.dumps(QA_RESPONSE, ensure_ascii=False)}\n```"
        mock_llm.generate.return_value = LLMResponse(
            content=fenced,
            latency_ms=100,
            input_tokens=50,
            output_tokens=200,
        )
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_qa(_make_session())
        assert "questions" in result.content_data

    async def test_passes_json_response_format(self) -> None:
        """Should pass response_format='json' to LLM provider."""
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_qa(_make_session())

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["response_format"] == "json"

    async def test_qa_uses_sufficient_max_tokens(self) -> None:
        """QA generation should use >= 4000 max_tokens for Chinese content."""
        mock_llm = _make_mock_llm(QA_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_qa(_make_session())

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["max_tokens"] >= 4000

    async def test_llm_returns_unparseable_json(self) -> None:
        """When LLM returns non-JSON, ValueError should be raised."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = LLMResponse(
            content="This is not JSON at all",
            latency_ms=100,
            input_tokens=50,
            output_tokens=200,
        )
        gen = StoryContentGenerator(mock_llm)
        with pytest.raises(ValueError, match="could not be parsed as JSON"):
            await gen.generate_qa(_make_session())


# =============================================================================
# T049 — generate_song
# =============================================================================


SONG_RESPONSE = {
    "lyrics": "超人力霸王飛呀飛，\n幫助小朋友不怕黑！\n勇敢的心最厲害，\n大家一起來學習！",
    "suno_prompt": "A cheerful children's song about a superhero helping kids be brave",
}


@pytest.mark.asyncio
class TestGenerateSong:
    """T049 — generate_song unit tests."""

    async def test_returns_story_generated_content(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        session = _make_session()
        result = await gen.generate_song(session)
        assert result.session_id == session.id
        assert result.content_type == GeneratedContentType.SONG

    async def test_content_type_is_song(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_song(_make_session())
        assert result.content_type == "song"

    async def test_content_data_has_lyrics(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_song(_make_session())
        assert "lyrics" in result.content_data
        assert isinstance(result.content_data["lyrics"], str)
        assert len(result.content_data["lyrics"]) > 0

    async def test_content_data_has_suno_prompt(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_song(_make_session())
        assert "suno_prompt" in result.content_data
        assert isinstance(result.content_data["suno_prompt"], str)

    async def test_content_data_has_generated_at(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_song(_make_session())
        assert "generated_at" in result.content_data

    async def test_calls_llm_with_system_and_user(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_song(_make_session())

        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    async def test_user_prompt_includes_child_info(self) -> None:
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_song(_make_session())

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        user_content = messages[1].content
        assert "5" in user_content  # age
        assert "超人力霸王" in user_content  # character

    async def test_llm_returns_markdown_fenced_json(self) -> None:
        mock_llm = AsyncMock()
        fenced = f"```json\n{json.dumps(SONG_RESPONSE, ensure_ascii=False)}\n```"
        mock_llm.generate.return_value = LLMResponse(
            content=fenced,
            latency_ms=100,
            input_tokens=50,
            output_tokens=200,
        )
        gen = StoryContentGenerator(mock_llm)
        result = await gen.generate_song(_make_session())
        assert "lyrics" in result.content_data
        assert "suno_prompt" in result.content_data

    async def test_passes_json_response_format(self) -> None:
        """Should pass response_format='json' to LLM provider."""
        mock_llm = _make_mock_llm(SONG_RESPONSE)
        gen = StoryContentGenerator(mock_llm)
        await gen.generate_song(_make_session())

        call_kwargs = mock_llm.generate.call_args.kwargs
        assert call_kwargs["response_format"] == "json"
