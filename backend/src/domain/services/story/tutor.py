"""Tutor service for StoryPal US5 — 適齡萬事通.

Provides age-appropriate Q&A and word chain game via LLM.
"""

from __future__ import annotations

import logging
from typing import Any

from src.application.interfaces.llm_provider import ILLMProvider, LLMMessage
from src.domain.services.story.prompts import build_tutor_system_prompt

logger = logging.getLogger(__name__)


class TutorService:
    """Age-appropriate tutor for children's questions and word games."""

    def __init__(self, llm_provider: ILLMProvider) -> None:
        self._llm = llm_provider

    async def answer_question(
        self,
        question: str,
        child_age: int,
        history: list[dict[str, str]],
    ) -> str:
        """Answer a child's question in <=3 sentences."""
        system = build_tutor_system_prompt(child_age)
        messages: list[LLMMessage] = [LLMMessage(role="system", content=system)]

        # Append conversation history
        for entry in history[-10:]:
            messages.append(LLMMessage(role=entry.get("role", "user"), content=entry["content"]))

        messages.append(LLMMessage(role="user", content=question))

        response = await self._llm.generate(
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )
        return response.content

    async def play_word_game(
        self,
        word: str,
        game_type: str,
        child_age: int,
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Play a word chain game, returning the next word and linking character."""
        system = build_tutor_system_prompt(child_age, game_type=game_type)
        messages: list[LLMMessage] = [LLMMessage(role="system", content=system)]

        for entry in history[-10:]:
            messages.append(LLMMessage(role=entry.get("role", "user"), content=entry["content"]))

        if word:
            prompt = (
                f"我們在玩詞語接龍（{game_type}）。"
                f"我說的詞語是「{word}」，"
                f"請接一個以「{word[-1]}」開頭的詞語。"
                f"回覆格式：先說你接的詞語，再鼓勵孩子接下一個。"
            )
        else:
            prompt = (
                f"我們來玩詞語接龍（{game_type}）！"
                f"請你先說一個簡單的詞語開始，然後告訴我接下來要接哪個字開頭的詞語。"
            )

        messages.append(LLMMessage(role="user", content=prompt))

        response = await self._llm.generate(
            messages=messages,
            max_tokens=200,
            temperature=0.8,
        )

        # Extract word info from response
        text = response.content.strip()
        # Best-effort extraction of the word the tutor said
        current_word = text.split("」")[0].split("「")[-1] if "「" in text else text.split("，")[0]
        next_char = current_word[-1] if current_word else ""

        return {
            "text": text,
            "current_word": current_word,
            "next_char": next_char,
        }
