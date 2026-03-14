"""Agent API routes — ADK-powered story creation."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.infrastructure.agents.story_agent import run_story_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


class StoryAgentRequest(BaseModel):
    """Request body for the ADK story agent."""

    theme: str = Field(..., description="Story theme or topic", min_length=1, max_length=200)
    age_group: str = Field(
        default="3-6",
        description="Target age group (e.g., '3-6', '6-9')",
    )


class StoryAgentResponse(BaseModel):
    """Response from the ADK story agent."""

    story: str = Field(..., description="Generated story content")
    theme: str = Field(..., description="Original theme")
    age_group: str = Field(..., description="Target age group")
    agent: str = Field(..., description="Agent name")
    session_id: str = Field(..., description="ADK session ID")


@router.post("/story", response_model=StoryAgentResponse)
async def create_story_with_agent(request: StoryAgentRequest) -> StoryAgentResponse:
    """Use ADK agent to create a children's story.

    The agent orchestrates story text generation, image creation,
    and narration using Gemini models.
    """
    result = await run_story_agent(
        theme=request.theme,
        age_group=request.age_group,
    )
    return StoryAgentResponse(**result)
