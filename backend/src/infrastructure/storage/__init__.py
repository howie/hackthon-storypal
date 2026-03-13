"""Storage Layer - Storage service implementations."""

from src.infrastructure.storage.factory import create_storage_service
from src.infrastructure.storage.local_storage import LocalStorage

# Alias for backward compatibility
LocalStorageService = LocalStorage

# GCS is optional - only import if google-cloud-storage is available
try:
    from src.infrastructure.storage.gcs_storage import GCSStorageService
except ImportError:
    GCSStorageService = None  # type: ignore

__all__ = [
    "LocalStorage",
    "LocalStorageService",
    "GCSStorageService",
    "create_storage_service",
]
