"""Unit tests for StoryEngine.generate_image_prompts().

Feature: 019-story-pixel-images (T018)
Tests:
  - LLM called with IMAGE_PROMPT_SYSTEM_PROMPT and formatted story text
  - JSON list response parsed into ImagePromptItem list
  - JSON with "prompts" key parsed correctly
  - Markdown-fenced JSON parsed correctly
  - Invalid JSON raises ValueError
  - Empty items list returns empty result (no crash)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.story import ImagePromptItem
from src.domain.services.story.engine import StoryEngine
from src.domain.services.story.prompts import IMAGE_PROMPT_SYSTEM_PROMPT


@dataclass
class FakeTurn:
    """Minimal turn-like object for testing."""

    turn_number: int
    content: str
    character_name: str | None = None


@dataclass
class FakeLLMResponse:
    content: str


def _make_engine(llm_response_text: str) -> StoryEngine:
    """Create a StoryEngine with a mock LLM that returns the given text."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value=FakeLLMResponse(content=llm_response_text))

    return StoryEngine(mock_llm)


# =============================================================================
# Successful parsing
# =============================================================================


@pytest.mark.asyncio
async def test_parse_json_list() -> None:
    """LLM returns a plain JSON list — parsed into ImagePromptItem list."""
    items = [
        {
            "turn_number": 2,
            "image_prompt": "pixel art style, a fox in a forest",
            "scene_description": "小狐狸在森林裡",
        },
        {
            "turn_number": 5,
            "image_prompt": "pixel art style, a fox by a river",
            "scene_description": "小狐狸來到河邊",
        },
    ]
    engine = _make_engine(json.dumps(items))
    turns = [
        FakeTurn(turn_number=1, content="從前從前", character_name="旁白"),
        FakeTurn(turn_number=2, content="小狐狸走進森林", character_name="小狐狸"),
        FakeTurn(turn_number=5, content="他來到河邊"),
    ]

    result = await engine.generate_image_prompts(turns)

    assert len(result) == 2
    assert isinstance(result[0], ImagePromptItem)
    assert result[0].turn_number == 2
    assert "fox" in result[0].image_prompt
    assert result[1].scene_description == "小狐狸來到河邊"


@pytest.mark.asyncio
async def test_parse_dict_with_prompts_key() -> None:
    """LLM returns {"prompts": [...]} — parsed correctly."""
    data = {
        "prompts": [
            {
                "turn_number": 1,
                "image_prompt": "pixel art style, forest",
                "scene_description": "森林",
            }
        ]
    }
    engine = _make_engine(json.dumps(data))

    result = await engine.generate_image_prompts([FakeTurn(1, "故事開始")])

    assert len(result) == 1
    assert result[0].turn_number == 1


@pytest.mark.asyncio
async def test_parse_markdown_fenced_json() -> None:
    """LLM wraps JSON in ```json ... ``` — parsed correctly."""
    items = [
        {
            "turn_number": 3,
            "image_prompt": "pixel art style, cave",
            "scene_description": "洞穴",
        }
    ]
    text = f"```json\n{json.dumps(items)}\n```"
    engine = _make_engine(text)

    result = await engine.generate_image_prompts([FakeTurn(3, "洞穴探險")])

    assert len(result) == 1
    assert result[0].scene_description == "洞穴"


# =============================================================================
# LLM prompt verification
# =============================================================================


@pytest.mark.asyncio
async def test_llm_called_with_correct_prompt() -> None:
    """Verify LLM receives IMAGE_PROMPT_SYSTEM_PROMPT and formatted turn text."""
    engine = _make_engine("[]")
    turns = [
        FakeTurn(turn_number=1, content="很久很久以前", character_name="旁白"),
        FakeTurn(turn_number=2, content="小熊出發了", character_name=None),
    ]

    await engine.generate_image_prompts(turns)

    call_args = engine._llm.generate.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]

    # System message should be IMAGE_PROMPT_SYSTEM_PROMPT
    assert messages[0].role == "system"
    assert messages[0].content == IMAGE_PROMPT_SYSTEM_PROMPT

    # User message should contain formatted turns
    user_content = messages[1].content
    assert "段落 1: [旁白] 很久很久以前" in user_content
    assert "段落 2: [旁白] 小熊出發了" in user_content

    # Verify generation parameters
    assert call_args.kwargs.get("response_format") == "json"
    assert call_args.kwargs.get("temperature") == 0.4


# =============================================================================
# Error handling
# =============================================================================


@pytest.mark.asyncio
async def test_invalid_json_raises_value_error() -> None:
    """Completely unparseable text raises ValueError."""
    engine = _make_engine("This is not JSON at all, just regular text about a story")

    with pytest.raises(ValueError, match="Failed to parse"):
        await engine.generate_image_prompts([FakeTurn(1, "text")])


@pytest.mark.asyncio
async def test_empty_items_returns_empty_list() -> None:
    """LLM returns empty array — returns empty list without error."""
    engine = _make_engine("[]")

    result = await engine.generate_image_prompts([FakeTurn(1, "text")])

    assert result == []


@pytest.mark.asyncio
async def test_non_dict_items_skipped() -> None:
    """Non-dict items in the array are silently skipped."""
    items = [
        "not a dict",
        {"turn_number": 1, "image_prompt": "pixel art style, test", "scene_description": "測試"},
        42,
    ]
    engine = _make_engine(json.dumps(items))

    result = await engine.generate_image_prompts([FakeTurn(1, "text")])

    assert len(result) == 1
    assert result[0].turn_number == 1
