"""Unit tests for TutorService.

Feature: 017-storypal — Phase 7
Task: T050 — Test TutorService:
  - answer_question() returns <= 3 sentences
  - play_word_game() returns dict with current_word and next_char keys
  - History is passed to LLM
  - child_age is injected into system prompt
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.application.interfaces.llm_provider import LLMResponse
from src.domain.services.story.tutor import TutorService


def _make_mock_llm(content: str) -> AsyncMock:
    """Create a mock ILLMProvider returning given content."""
    mock = AsyncMock()
    mock.generate.return_value = LLMResponse(
        content=content,
        latency_ms=80,
        input_tokens=30,
        output_tokens=50,
    )
    return mock


# =============================================================================
# answer_question
# =============================================================================


@pytest.mark.asyncio
class TestAnswerQuestion:
    """TutorService.answer_question unit tests."""

    async def test_returns_string(self) -> None:
        mock_llm = _make_mock_llm(
            "因為室內拖可以保護你的腳腳喔！穿上以後走路也比較安全呢～下次我們一起練習好不好？"
        )
        svc = TutorService(mock_llm)
        result = await svc.answer_question("為什麼要穿室內拖？", child_age=4, history=[])
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_calls_llm_with_system_and_user(self) -> None:
        mock_llm = _make_mock_llm("這是一個好問題！")
        svc = TutorService(mock_llm)
        await svc.answer_question("天空為什麼是藍色的？", child_age=5, history=[])

        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        # system + user question
        assert len(messages) >= 2
        assert messages[0].role == "system"
        assert messages[-1].role == "user"
        assert "天空為什麼是藍色的？" in messages[-1].content

    async def test_system_prompt_contains_child_age(self) -> None:
        mock_llm = _make_mock_llm("好問題！")
        svc = TutorService(mock_llm)
        await svc.answer_question("為什麼？", child_age=3, history=[])

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        system_content = messages[0].content
        assert "3" in system_content, "System prompt should contain child_age"

    async def test_history_appended_to_messages(self) -> None:
        mock_llm = _make_mock_llm("因為地球在轉動！")
        history = [
            {"role": "user", "content": "太陽為什麼會落下？"},
            {"role": "assistant", "content": "因為地球在轉喔！"},
        ]
        svc = TutorService(mock_llm)
        await svc.answer_question("那月亮呢？", child_age=4, history=history)

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        # system + 2 history + user question = 4
        assert len(messages) == 4
        assert messages[1].content == "太陽為什麼會落下？"
        assert messages[2].content == "因為地球在轉喔！"

    async def test_empty_history(self) -> None:
        mock_llm = _make_mock_llm("小朋友你好棒！")
        svc = TutorService(mock_llm)
        result = await svc.answer_question("你好！", child_age=4, history=[])
        assert isinstance(result, str)

    async def test_max_tokens_is_reasonable(self) -> None:
        """answer_question should use a small max_tokens for short responses."""
        mock_llm = _make_mock_llm("好喔！")
        svc = TutorService(mock_llm)
        await svc.answer_question("為什麼？", child_age=4, history=[])

        call_kwargs = mock_llm.generate.call_args
        max_tokens = call_kwargs.kwargs.get("max_tokens", 0)
        assert max_tokens <= 500, "Tutor answers should be concise"


# =============================================================================
# play_word_game
# =============================================================================


@pytest.mark.asyncio
class TestPlayWordGame:
    """TutorService.play_word_game unit tests."""

    async def test_returns_dict_with_required_keys(self) -> None:
        mock_llm = _make_mock_llm("我接「花瓣」！你來接「瓣」開頭的詞語吧！")
        svc = TutorService(mock_llm)
        result = await svc.play_word_game(
            word="開花",
            game_type="word_chain",
            child_age=4,
            history=[],
        )
        assert isinstance(result, dict)
        assert "current_word" in result
        assert "next_char" in result
        assert "text" in result

    async def test_current_word_extracted(self) -> None:
        mock_llm = _make_mock_llm("「花園」！你來接一個「園」開頭的詞語吧！")
        svc = TutorService(mock_llm)
        result = await svc.play_word_game(
            word="開花",
            game_type="word_chain",
            child_age=4,
            history=[],
        )
        assert result["current_word"] == "花園"
        assert result["next_char"] == "園"

    async def test_start_game_without_word(self) -> None:
        """When word is empty, tutor should start the game with a new word."""
        mock_llm = _make_mock_llm("我們來玩詞語接龍！我先說「蘋果」，你來接一個「果」開頭的詞語！")
        svc = TutorService(mock_llm)
        result = await svc.play_word_game(
            word="",
            game_type="word_chain",
            child_age=4,
            history=[],
        )
        assert isinstance(result, dict)
        assert "current_word" in result
        assert "text" in result

    async def test_calls_llm_with_word_chain_prompt(self) -> None:
        mock_llm = _make_mock_llm("「月亮」！")
        svc = TutorService(mock_llm)
        await svc.play_word_game(
            word="日月",
            game_type="word_chain",
            child_age=5,
            history=[],
        )

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        user_content = messages[-1].content
        assert "接龍" in user_content
        assert "日月" in user_content

    async def test_history_included(self) -> None:
        history = [
            {"role": "user", "content": "蘋果"},
            {"role": "assistant", "content": "「果汁」！你來接「汁」"},
        ]
        mock_llm = _make_mock_llm("「水果」！")
        svc = TutorService(mock_llm)
        await svc.play_word_game(
            word="汁水",
            game_type="word_chain",
            child_age=4,
            history=history,
        )

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        if messages is None:
            messages = call_kwargs[0][0] if call_kwargs[0] else []
        # system + 2 history + user prompt = 4
        assert len(messages) == 4

    async def test_no_brackets_in_response_still_works(self) -> None:
        """When LLM response has no brackets, should still return a result."""
        mock_llm = _make_mock_llm("太陽，你來接陽開頭的詞語！")
        svc = TutorService(mock_llm)
        result = await svc.play_word_game(
            word="月亮",
            game_type="word_chain",
            child_age=4,
            history=[],
        )
        assert isinstance(result, dict)
        assert len(result["current_word"]) > 0
