"""API Routes - FastAPI route handlers for StoryPal."""

from fastapi import APIRouter

from src.presentation.api.routes import (
    agent,
    auth,
    dj,
    health,
    story,
    story_ws,
    tutor,
    tutor_ws,
)

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(agent.router)
api_router.include_router(auth.router)
api_router.include_router(story.router)
api_router.include_router(story_ws.router, prefix="/story", tags=["StoryPal WebSocket"])
api_router.include_router(tutor.router)
api_router.include_router(tutor_ws.router, prefix="/tutor", tags=["Tutor WebSocket"])
api_router.include_router(dj.router)  # Magic DJ Controller

__all__ = ["api_router"]
