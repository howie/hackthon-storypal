"""Storage Layer - Storage service implementations."""

from src.infrastructure.storage.dj_audio_storage import DJAudioStorageService
from src.infrastructure.storage.factory import create_storage_service
from src.infrastructure.storage.local_storage import LocalStorage

# Alias for backward compatibility
LocalStorageService = LocalStorage

# S3 is optional - only import if aioboto3 is available
try:
    from src.infrastructure.storage.s3_storage import S3StorageService
except ImportError:
    S3StorageService = None  # type: ignore

# GCS is optional - only import if google-cloud-storage is available
try:
    from src.infrastructure.storage.gcs_storage import GCSStorageService
except ImportError:
    GCSStorageService = None  # type: ignore

__all__ = [
    "LocalStorage",
    "LocalStorageService",
    "S3StorageService",
    "GCSStorageService",
    "create_storage_service",
    # DJ (Feature 011)
    "DJAudioStorageService",
]
