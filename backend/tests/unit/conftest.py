"""Unit test fixtures.

Overrides root conftest fixtures that are unnecessary for unit tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """No-op override: unit tests don't interact with the app's rate limiter."""
