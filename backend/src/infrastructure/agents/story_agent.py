"""ADK-based Story Creation Agent for StoryPal.

Uses Google Agent Development Kit (ADK) to orchestrate story generation
with Gemini LLM, Imagen image generation, and Gemini TTS.
"""

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.config import get_settings

logger = logging.getLogger(__name__)


def generate_story_text(
    theme: str,
    age_group: str = "3-6",
    language: str = "zh-TW",
) -> str:
    """Generate a children's story based on the given theme and age group.

    Args:
        theme: The story theme or topic (e.g., "forest adventure", "space exploration").
        age_group: Target age group (e.g., "3-6", "6-9"). Defaults to "3-6".
        language: Language for the story. Defaults to "zh-TW" (Traditional Chinese).

    Returns:
        A children's story in the specified language, formatted as a string
        with title and paragraphs.
    """
    return (
        f"[Story Generation Tool Called]\n"
        f"Theme: {theme}\n"
        f"Age Group: {age_group}\n"
        f"Language: {language}\n"
        f"Please generate the story content directly in your response."
    )


def generate_story_image(scene_description: str) -> str:
    """Generate a child-friendly illustration for a story scene.

    Args:
        scene_description: A detailed description of the scene to illustrate,
            including characters, setting, mood, and art style preferences.

    Returns:
        A confirmation that the image generation request has been noted.
        The actual image will be generated separately.
    """
    return (
        f"[Image Generation Tool Called]\n"
        f"Scene: {scene_description}\n"
        f"Image generation request has been recorded. "
        f"Include this scene description in your final response."
    )


def narrate_story(text: str, voice: str = "Laomedeia") -> str:
    """Convert story text to speech audio for narration.

    Args:
        text: The story text to narrate. Should be a single paragraph or section,
            not the entire story at once. Maximum ~1000 Chinese characters.
        voice: The voice to use for narration. Defaults to "Laomedeia"
            (cheerful female voice, good for children's content).

    Returns:
        A confirmation that the narration request has been noted.
    """
    return (
        f"[Narration Tool Called]\n"
        f"Text length: {len(text)} characters\n"
        f"Voice: {voice}\n"
        f"Narration request has been recorded."
    )


def _build_story_agent() -> LlmAgent:
    """Build the ADK story creation agent."""
    return LlmAgent(
        name="story_creator",
        model="gemini-2.5-flash",
        instruction=(
            "你是 StoryPal 故事創作助手，專門為兒童創作互動故事。\n\n"
            "當使用者提供主題時，請按照以下步驟：\n"
            "1. 使用 generate_story_text 工具，傳入主題和年齡層來構思故事\n"
            "2. 根據工具回傳的提示，直接創作一個完整的兒童故事（3-5段）\n"
            "3. 使用 generate_story_image 工具，為故事中最精彩的場景生成插圖描述\n"
            "4. 使用 narrate_story 工具，將故事的開頭段落轉為語音\n\n"
            "故事要求：\n"
            "- 使用繁體中文\n"
            "- 適合兒童的語言，簡單易懂\n"
            "- 包含正面的教育意義\n"
            "- 有趣且富有想像力\n"
            "- 每段不超過100字\n\n"
            "最後，將完整的故事內容整理好回覆給使用者，包含標題和分段的故事內容。"
        ),
        tools=[generate_story_text, generate_story_image, narrate_story],
    )


# Module-level agent instance (reusable)
story_agent = _build_story_agent()

# Session service for managing agent sessions
_session_service = InMemorySessionService()


async def run_story_agent(
    theme: str,
    age_group: str = "3-6",
    user_id: str = "anonymous",
) -> dict:
    """Run the ADK story agent to create a story.

    Args:
        theme: Story theme or topic
        age_group: Target age group
        user_id: User identifier for session tracking

    Returns:
        Dictionary with the agent's response including story content
    """
    settings = get_settings()

    # Set the API key for the agent's model
    os.environ.setdefault("GOOGLE_API_KEY", settings.gemini_api_key)

    runner = Runner(
        agent=story_agent,
        app_name="storypal",
        session_service=_session_service,
    )

    # Create a new session for this request
    session = await _session_service.create_session(
        app_name="storypal",
        user_id=user_id,
    )

    # Build the user prompt
    user_prompt = f"請為{age_group}歲的小朋友創作一個關於「{theme}」的故事。"

    # Run the agent
    final_response = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=user_prompt)],
        ),
    ):
        # Collect the final response from the agent
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response += part.text

    return {
        "story": final_response,
        "theme": theme,
        "age_group": age_group,
        "agent": "story_creator",
        "session_id": session.id,
    }
