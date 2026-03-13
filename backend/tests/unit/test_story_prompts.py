"""Unit tests for StoryPal prompt functions and templates.

Feature: 017-storypal — Phase 2
Task: T046 — Test build_custom_system_prompt with various ChildConfig inputs;
assert SONG/QA/INTERACTIVE prompt templates contain required keywords.
"""

from __future__ import annotations

from src.domain.entities.story import ChildConfig
from src.domain.services.story.prompts import (
    EMOTION_LABELS,
    INTERACTIVE_CHOICES_SYSTEM_PROMPT,
    INTERACTIVE_CHOICES_USER_PROMPT_TEMPLATE,
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT_TEMPLATE,
    SONG_SYSTEM_PROMPT,
    SONG_USER_PROMPT_TEMPLATE,
    TUTOR_GAMES,
    VALUE_LABELS,
    build_custom_system_prompt,
    build_tutor_system_prompt,
    get_available_games,
)

# =============================================================================
# VALUE_LABELS / EMOTION_LABELS
# =============================================================================


class TestValueLabels:
    """VALUE_LABELS dict must contain all valid value keys."""

    def test_contains_all_value_keys(self) -> None:
        expected_keys = {
            "empathy_care",
            "honesty_responsibility",
            "respect_cooperation",
            "curiosity_exploration",
            "self_management",
            "resilience",
        }
        assert expected_keys.issubset(set(VALUE_LABELS.keys()))

    def test_labels_are_chinese(self) -> None:
        for key, label in VALUE_LABELS.items():
            assert isinstance(label, str)
            assert len(label) > 0, f"VALUE_LABELS[{key!r}] is empty"


class TestEmotionLabels:
    """EMOTION_LABELS dict must contain all valid emotion keys."""

    def test_contains_all_emotion_keys(self) -> None:
        expected_keys = {
            "happiness",
            "anger",
            "sadness",
            "fear",
            "surprise",
            "disgust",
            "pride",
            "shame_guilt",
            "jealousy",
        }
        assert expected_keys.issubset(set(EMOTION_LABELS.keys()))

    def test_labels_are_chinese(self) -> None:
        for key, label in EMOTION_LABELS.items():
            assert isinstance(label, str)
            assert len(label) > 0, f"EMOTION_LABELS[{key!r}] is empty"


# =============================================================================
# build_custom_system_prompt
# =============================================================================


class TestBuildCustomSystemPrompt:
    """build_custom_system_prompt must produce a system prompt
    incorporating all ChildConfig fields."""

    def test_default_child_config(self) -> None:
        """Default ChildConfig should still produce a valid prompt."""
        config = ChildConfig()
        prompt = build_custom_system_prompt(config)
        assert isinstance(prompt, str)
        assert len(prompt) > 50, "Prompt should be non-trivial"

    def test_contains_age(self) -> None:
        config = ChildConfig(age=5)
        prompt = build_custom_system_prompt(config)
        assert "5" in prompt, "Prompt should mention the child's age"

    def test_contains_learning_goals(self) -> None:
        config = ChildConfig(learning_goals="自己穿室內拖")
        prompt = build_custom_system_prompt(config)
        assert "自己穿室內拖" in prompt

    def test_contains_favorite_character(self) -> None:
        config = ChildConfig(favorite_character="超人力霸王")
        prompt = build_custom_system_prompt(config)
        assert "超人力霸王" in prompt

    def test_contains_selected_values_labels(self) -> None:
        config = ChildConfig(selected_values=["empathy_care", "resilience"])
        prompt = build_custom_system_prompt(config)
        assert VALUE_LABELS["empathy_care"] in prompt
        assert VALUE_LABELS["resilience"] in prompt

    def test_contains_selected_emotions_labels(self) -> None:
        config = ChildConfig(selected_emotions=["pride", "happiness"])
        prompt = build_custom_system_prompt(config)
        assert EMOTION_LABELS["pride"] in prompt
        assert EMOTION_LABELS["happiness"] in prompt

    def test_empty_values_still_valid(self) -> None:
        """When no values selected, prompt should still be valid."""
        config = ChildConfig(selected_values=[])
        prompt = build_custom_system_prompt(config)
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_empty_emotions_still_valid(self) -> None:
        """When no emotions selected, prompt should still be valid."""
        config = ChildConfig(selected_emotions=[])
        prompt = build_custom_system_prompt(config)
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_full_config(self) -> None:
        """A fully-populated ChildConfig should produce a comprehensive prompt."""
        config = ChildConfig(
            age=4,
            learning_goals="自己穿室內拖",
            selected_values=["empathy_care", "self_management"],
            selected_emotions=["pride", "fear"],
            favorite_character="超人力霸王",
        )
        prompt = build_custom_system_prompt(config)
        assert "4" in prompt
        assert "自己穿室內拖" in prompt
        assert "超人力霸王" in prompt
        assert VALUE_LABELS["empathy_care"] in prompt
        assert VALUE_LABELS["self_management"] in prompt
        assert EMOTION_LABELS["pride"] in prompt
        assert EMOTION_LABELS["fear"] in prompt

    def test_no_favorite_character_uses_fallback(self) -> None:
        """When favorite_character is empty, prompt should use a generic fallback."""
        config = ChildConfig(favorite_character="")
        prompt = build_custom_system_prompt(config)
        # Should not crash and should still be a valid prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 50


# =============================================================================
# SONG prompt templates
# =============================================================================


class TestSongPromptTemplates:
    """SONG_SYSTEM_PROMPT and SONG_USER_PROMPT_TEMPLATE must contain
    required keywords for children's song generation."""

    def test_song_system_prompt_exists(self) -> None:
        assert isinstance(SONG_SYSTEM_PROMPT, str)
        assert len(SONG_SYSTEM_PROMPT) > 50

    def test_song_system_prompt_mentions_children(self) -> None:
        assert any(
            kw in SONG_SYSTEM_PROMPT for kw in ("兒歌", "歌詞", "孩子", "children", "song")
        ), "SONG_SYSTEM_PROMPT should mention children's songs"

    def test_song_system_prompt_mentions_repetition(self) -> None:
        assert any(kw in SONG_SYSTEM_PROMPT for kw in ("重複", "repetitive", "repeat", "副歌")), (
            "SONG_SYSTEM_PROMPT should mention repetition for children's songs"
        )

    def test_song_system_prompt_mentions_taiwanese(self) -> None:
        assert any(kw in SONG_SYSTEM_PROMPT for kw in ("台灣", "繁體中文", "Taiwan")), (
            "SONG_SYSTEM_PROMPT should mention Taiwanese language"
        )

    def test_song_user_prompt_template_exists(self) -> None:
        assert isinstance(SONG_USER_PROMPT_TEMPLATE, str)
        assert len(SONG_USER_PROMPT_TEMPLATE) > 20

    def test_song_user_prompt_mentions_suno(self) -> None:
        combined = SONG_SYSTEM_PROMPT + SONG_USER_PROMPT_TEMPLATE
        assert any(
            kw in combined for kw in ("suno", "Suno", "SUNO", "suno_prompt", "英文 prompt")
        ), "Song prompts should mention Suno prompt generation"


# =============================================================================
# QA prompt templates
# =============================================================================


class TestQAPromptTemplates:
    """QA_SYSTEM_PROMPT and QA_USER_PROMPT_TEMPLATE must enforce
    Q&A interaction structure."""

    def test_qa_system_prompt_exists(self) -> None:
        assert isinstance(QA_SYSTEM_PROMPT, str)
        assert len(QA_SYSTEM_PROMPT) > 50

    def test_qa_system_prompt_mentions_questions(self) -> None:
        assert any(kw in QA_SYSTEM_PROMPT for kw in ("問題", "question", "Q&A", "題")), (
            "QA_SYSTEM_PROMPT should mention questions"
        )

    def test_qa_system_prompt_mentions_encouragement(self) -> None:
        assert any(kw in QA_SYSTEM_PROMPT for kw in ("鼓勵", "encouragement", "稱讚")), (
            "QA_SYSTEM_PROMPT should mention encouragement"
        )

    def test_qa_system_prompt_mentions_hint(self) -> None:
        assert any(kw in QA_SYSTEM_PROMPT for kw in ("提示", "hint", "引導")), (
            "QA_SYSTEM_PROMPT should mention hints"
        )

    def test_qa_system_prompt_mentions_closing(self) -> None:
        assert any(kw in QA_SYSTEM_PROMPT for kw in ("結束語", "closing", "結尾")), (
            "QA_SYSTEM_PROMPT should mention closing message"
        )

    def test_qa_prompts_mention_json(self) -> None:
        combined = QA_SYSTEM_PROMPT + QA_USER_PROMPT_TEMPLATE
        assert any(kw in combined for kw in ("JSON", "json")), (
            "QA prompts should require JSON output"
        )

    def test_qa_user_prompt_template_exists(self) -> None:
        assert isinstance(QA_USER_PROMPT_TEMPLATE, str)
        assert len(QA_USER_PROMPT_TEMPLATE) > 20


# =============================================================================
# INTERACTIVE_CHOICES prompt templates
# =============================================================================


class TestInteractiveChoicesPromptTemplates:
    """INTERACTIVE_CHOICES prompts must enforce choice-node structure."""

    def test_interactive_choices_system_prompt_exists(self) -> None:
        assert isinstance(INTERACTIVE_CHOICES_SYSTEM_PROMPT, str)
        assert len(INTERACTIVE_CHOICES_SYSTEM_PROMPT) > 50

    def test_interactive_choices_mentions_options(self) -> None:
        assert any(
            kw in INTERACTIVE_CHOICES_SYSTEM_PROMPT for kw in ("選項", "選擇", "option", "choice")
        ), "INTERACTIVE_CHOICES_SYSTEM_PROMPT should mention options/choices"

    def test_interactive_choices_mentions_timeout(self) -> None:
        assert any(
            kw in INTERACTIVE_CHOICES_SYSTEM_PROMPT for kw in ("超時", "timeout", "提示語", "等待")
        ), "INTERACTIVE_CHOICES_SYSTEM_PROMPT should mention timeout hints"

    def test_interactive_choices_mentions_positive_ending(self) -> None:
        assert any(
            kw in INTERACTIVE_CHOICES_SYSTEM_PROMPT for kw in ("正向", "正面", "positive")
        ), "INTERACTIVE_CHOICES_SYSTEM_PROMPT should mention positive outcomes"

    def test_interactive_choices_prompts_mention_json(self) -> None:
        combined = INTERACTIVE_CHOICES_SYSTEM_PROMPT + INTERACTIVE_CHOICES_USER_PROMPT_TEMPLATE
        assert any(kw in combined for kw in ("JSON", "json")), (
            "Interactive choices prompts should require JSON output"
        )

    def test_interactive_choices_user_prompt_template_exists(self) -> None:
        assert isinstance(INTERACTIVE_CHOICES_USER_PROMPT_TEMPLATE, str)
        assert len(INTERACTIVE_CHOICES_USER_PROMPT_TEMPLATE) > 20


# =============================================================================
# TUTOR_SYSTEM_PROMPT
# =============================================================================


class TestBuildTutorSystemPrompt:
    """build_tutor_system_prompt must produce correct prompts."""

    def test_basic_prompt_contains_teacher_role(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4)
        assert any(kw in prompt for kw in ("老師", "teacher", "早教", "幼稚園"))

    def test_prompt_contains_taiwanese(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4)
        assert any(kw in prompt for kw in ("台灣", "繁體中文", "Taiwan"))

    def test_prompt_contains_age(self) -> None:
        prompt = build_tutor_system_prompt(child_age=6)
        assert "6" in prompt

    def test_age_1_short_sentences(self) -> None:
        prompt = build_tutor_system_prompt(child_age=1)
        assert "5 個字" in prompt
        assert "2 句" in prompt

    def test_no_baby_talk_in_any_age(self) -> None:
        """Prompt must never instruct the model to use baby-talk / 疊字."""
        baby_talk_phrases = ["飯飯", "抱抱", "水水", "疊詞"]
        for age in range(1, 9):
            prompt = build_tutor_system_prompt(child_age=age)
            for phrase in baby_talk_phrases:
                # Allow negative instructions like "不要用疊字" or "不說飯飯"
                # but disallow positive instructions to USE them
                lines_with_phrase = [line for line in prompt.splitlines() if phrase in line]
                for line in lines_with_phrase:
                    assert any(neg in line for neg in ("不要", "不用", "不說")), (
                        f"Age {age}: found '{phrase}' without negation in: {line}"
                    )

    def test_correct_speech_rule_in_system_prompt(self) -> None:
        """System prompt should instruct correct adult speech."""
        prompt = build_tutor_system_prompt(child_age=4)
        assert "正確的大人說話方式" in prompt

    def test_age_4_medium_sentences(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4)
        assert "10 個字" in prompt

    def test_age_7_longer_sentences(self) -> None:
        prompt = build_tutor_system_prompt(child_age=7)
        assert "20 個字" in prompt
        assert "4 句" in prompt

    def test_no_game_type_no_game_rules(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4)
        assert "接龍規則" not in prompt
        assert "猜謎語規則" not in prompt

    def test_word_chain_game_injects_rules(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4, game_type="word_chain")
        assert "接龍規則" in prompt

    def test_riddles_game_injects_rules(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4, game_type="riddles")
        assert "猜謎語規則" in prompt

    def test_invalid_game_type_ignored(self) -> None:
        prompt = build_tutor_system_prompt(child_age=4, game_type="nonexistent")
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_all_game_types_produce_valid_prompt(self) -> None:
        for game_id in TUTOR_GAMES:
            prompt = build_tutor_system_prompt(child_age=5, game_type=game_id)
            assert isinstance(prompt, str)
            assert len(prompt) > 50


class TestGetAvailableGames:
    """get_available_games must filter by age."""

    def test_age_1_only_animal_sounds(self) -> None:
        games = get_available_games(1)
        ids = [g["id"] for g in games]
        assert ids == ["animal_sounds"]

    def test_age_2_only_animal_sounds(self) -> None:
        games = get_available_games(2)
        ids = [g["id"] for g in games]
        assert ids == ["animal_sounds"]

    def test_age_4_includes_word_chain_and_riddles(self) -> None:
        games = get_available_games(4)
        ids = [g["id"] for g in games]
        assert "animal_sounds" in ids
        assert "word_chain" in ids
        assert "riddles" in ids
        assert "antonyms" not in ids

    def test_age_5_includes_antonyms_and_story_chain(self) -> None:
        games = get_available_games(5)
        ids = [g["id"] for g in games]
        assert "antonyms" in ids
        assert "story_chain" in ids
        assert "brain_teasers" not in ids

    def test_age_7_includes_brain_teasers(self) -> None:
        games = get_available_games(7)
        ids = [g["id"] for g in games]
        assert "brain_teasers" in ids

    def test_returns_required_fields(self) -> None:
        games = get_available_games(5)
        for game in games:
            assert "id" in game
            assert "name" in game
            assert "description" in game
            assert "min_age" in game
            assert "max_age" in game


class TestTutorGamesDefinitions:
    """TUTOR_GAMES dict must have valid structure."""

    def test_all_games_have_required_keys(self) -> None:
        for game_id, game in TUTOR_GAMES.items():
            assert "name" in game, f"{game_id} missing name"
            assert "description" in game, f"{game_id} missing description"
            assert "min_age" in game, f"{game_id} missing min_age"
            assert "max_age" in game, f"{game_id} missing max_age"
            assert "prompt_rules" in game, f"{game_id} missing prompt_rules"

    def test_age_ranges_valid(self) -> None:
        for game_id, game in TUTOR_GAMES.items():
            assert 1 <= game["min_age"] <= game["max_age"] <= 8, f"{game_id} has invalid age range"
