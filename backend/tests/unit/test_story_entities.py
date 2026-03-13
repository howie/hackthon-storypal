"""Unit tests for StoryPal domain entities.

Regression guards for StoryTemplate and related dataclass construction.
Ensures required fields are always passed correctly.
"""

from __future__ import annotations

from src.domain.entities.story import (
    ChildConfig,
    SceneInfo,
    StoryCategory,
    StoryCharacter,
    StoryTemplate,
)


class TestStoryTemplateConstruction:
    """Regression guard: StoryTemplate must be constructed with all required fields."""

    def test_story_template_requires_all_fields(self) -> None:
        """Regression test: ensure all required fields are passed to StoryTemplate.

        This test guards against the bug where StoryTemplate.__init__() was
        called without 'scenes', 'opening_prompt', and 'system_prompt'.
        If anyone changes the dataclass and forgets to update construction
        sites, this test will turn red immediately.
        """
        template = StoryTemplate(
            name="test",
            description="desc",
            category=StoryCategory.ADVENTURE,
            target_age_min=3,
            target_age_max=8,
            language="zh-TW",
            characters=[],
            scenes=[],
            opening_prompt="",
            system_prompt="",
        )
        assert template.name == "test"
        assert template.scenes == []
        assert template.opening_prompt == ""
        assert template.system_prompt == ""

    def test_story_template_with_all_optional_fields(self) -> None:
        """StoryTemplate can carry characters and scenes without error."""
        char = StoryCharacter(
            name="小熊",
            description="a bear",
            voice_provider="gemini",
            voice_id="Kore",
        )
        scene = SceneInfo(name="森林", description="a forest")
        template = StoryTemplate(
            name="小熊的冒險",
            description="熊的故事",
            category=StoryCategory.FAIRY_TALE,
            target_age_min=3,
            target_age_max=6,
            language="zh-TW",
            characters=[char],
            scenes=[scene],
            opening_prompt="從前從前",
            system_prompt="你是一個說故事的人",
        )
        assert len(template.characters) == 1
        assert len(template.scenes) == 1
        assert template.category == StoryCategory.FAIRY_TALE

    def test_story_template_category_values(self) -> None:
        """StoryCategory should support all expected values."""
        assert StoryCategory.FAIRY_TALE == "fairy_tale"
        assert StoryCategory.ADVENTURE == "adventure"
        assert StoryCategory.SCIENCE == "science"
        assert StoryCategory.FABLE == "fable"
        assert StoryCategory.DAILY_LIFE == "daily_life"

    def test_child_config_defaults(self) -> None:
        """ChildConfig should have sensible defaults for all optional fields."""
        config = ChildConfig(age=5)
        assert config.age == 5
        assert config.learning_goals == ""
        assert config.selected_values == []
        assert config.selected_emotions == []
        assert config.favorite_character == ""
        assert config.voice_id is None

    def test_child_config_full(self) -> None:
        """ChildConfig can hold all child personalisation fields."""
        config = ChildConfig(
            age=4,
            learning_goals="自己穿鞋",
            selected_values=["empathy_care"],
            selected_emotions=["pride"],
            favorite_character="超人力霸王",
            voice_id="Kore",
        )
        assert config.favorite_character == "超人力霸王"
        assert "empathy_care" in config.selected_values
