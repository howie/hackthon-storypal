"""Storage service factory.

Selects the appropriate IStorageService implementation based on environment:
- ``AUDIO_BUCKET`` set  → GCSStorageService (production / Cloud Run)
- ``AUDIO_BUCKET`` unset → LocalStorage (local development)
"""

import logging
import os

from src.application.interfaces.storage_service import IStorageService
from src.infrastructure.storage.local_storage import LocalStorage

logger = logging.getLogger(__name__)


def create_storage_service() -> IStorageService:
    """Create the storage service configured for the current environment.

    Reads ``AUDIO_BUCKET`` and ``LOCAL_STORAGE_PATH`` from the environment.

    Returns:
        GCSStorageService if ``AUDIO_BUCKET`` is set, otherwise LocalStorage.
    """
    bucket = os.getenv("AUDIO_BUCKET")
    if bucket:
        from src.infrastructure.storage.gcs_storage import GCSStorageService

        logger.info("Storage: using GCS bucket=%s", bucket)
        return GCSStorageService(bucket_name=bucket)

    storage_path = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    logger.info("Storage: using LocalStorage path=%s", storage_path)
    return LocalStorage(base_path=storage_path)
