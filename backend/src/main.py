"""StoryPal API - Main application entry point."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from src.audio_config import configure_ffmpeg
from src.config import get_settings
from src.infrastructure.persistence.database import AsyncSessionLocal
from src.presentation.api import api_router
from src.presentation.api.middleware.error_handler import (
    RequestIdMiddleware,
    setup_error_handlers,
)
from src.presentation.api.middleware.rate_limit import (
    RateLimitMiddleware,
    default_rate_limiter,
)

# Ensure ffmpeg is available before any pydub usage
configure_ffmpeg()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    print(f"Starting {settings.app_name} in {settings.app_env} mode...")

    # Ensure storage directory exists
    storage_path = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    os.makedirs(storage_path, exist_ok=True)

    # Storage configuration check
    bucket = os.getenv("AUDIO_BUCKET")
    if bucket:
        logger.info("Storage: GCS bucket=%s", bucket)
    else:
        logger.warning(
            "Storage: using LOCAL filesystem (%s) — files will NOT survive container restart!",
            storage_path,
        )

    # Initialize providers on startup
    from src.presentation.api.dependencies import get_container

    container = get_container()
    print(f"TTS Providers: {list(container.get_tts_providers().keys())}")
    print(f"LLM Providers: {list(container.get_llm_providers().keys())}")

    # Clean up stuck story generation/synthesis jobs from previous run
    try:
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import select

        from src.infrastructure.persistence.models import StorySessionModel

        orphan_cutoff = datetime.now(UTC) - timedelta(minutes=30)

        async with AsyncSessionLocal() as cleanup_db:
            result = await cleanup_db.execute(select(StorySessionModel))
            for s in result.scalars().all():
                state = s.story_state or {}
                changed = False
                updated_at = s.updated_at
                is_orphan = updated_at is None or updated_at < orphan_cutoff
                if state.get("generation_status") == "generating":
                    state["generation_status"] = "failed"
                    state["generation_error"] = (
                        "Orphan task recovered: exceeded 30-minute timeout"
                        if is_orphan
                        else "Server restarted"
                    )
                    changed = True
                if state.get("synthesis_status") == "synthesizing":
                    state["synthesis_status"] = "failed"
                    state["synthesis_error"] = (
                        "Orphan task recovered: exceeded 30-minute timeout"
                        if is_orphan
                        else "Server restarted"
                    )
                    changed = True
                if changed:
                    s.story_state = state
            await cleanup_db.commit()
        print("Stuck story job cleanup completed")
    except Exception as exc:
        print(f"Stuck story job cleanup failed (non-fatal): {exc}")

    yield

    # Shutdown
    print(f"Shutting down {settings.app_name}...")


app = FastAPI(
    title=settings.app_name,
    description="StoryPal — AI-powered interactive storytelling and tutoring for kids",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Register unified error handlers
setup_error_handlers(app)

# Middleware (Starlette LIFO: last added = outermost)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=default_rate_limiter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)

# Serve audio files
_storage_path = os.getenv("LOCAL_STORAGE_PATH", "./storage")


@app.get("/files/{path:path}", include_in_schema=False)
async def serve_file(path: str) -> Response:
    """Proxy route that serves audio files from local storage or GCS."""
    local_path = Path(_storage_path) / path
    if local_path.exists():
        return FileResponse(str(local_path))

    bucket = os.getenv("AUDIO_BUCKET")
    if bucket:
        try:
            from src.infrastructure.storage.gcs_storage import GCSStorageService

            gcs = GCSStorageService(bucket_name=bucket)
            data = await gcs.download(path)
            suffix = Path(path).suffix.lower()
            media_type = (
                "audio/mpeg"
                if suffix == ".mp3"
                else "audio/wav"
                if suffix == ".wav"
                else "application/octet-stream"
            )
            return Response(content=data, media_type=media_type)
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("GCS fetch failed for path=%s: %s", path, exc)

    raise HTTPException(status_code=404, detail="File not found")
