"""Shared test fixtures and utilities."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear get_settings LRU cache before and after each test."""
    from src.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def sample_user_id() -> uuid.UUID:
    """Return a consistent test user ID."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")
