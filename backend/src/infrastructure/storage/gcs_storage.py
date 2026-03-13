"""Google Cloud Storage implementation of IStorageService.

Uses Application Default Credentials (ADC):
- Cloud Run: automatically uses the attached service account
- Local dev: requires GOOGLE_APPLICATION_CREDENTIALS env var pointing to a key file
"""

import asyncio
import logging

from src.application.interfaces.storage_service import IStorageService, StoredFile

logger = logging.getLogger(__name__)


class GCSStorageService(IStorageService):
    """GCS-backed storage service.

    All keys are stored as GCS object names (e.g. ``music/lyria/2025-01-01/abc.mp3``).
    URLs are always returned as ``/files/{key}`` so the ``/files/`` proxy in main.py
    handles serving transparently whether the file is local or in GCS.
    """

    def __init__(self, bucket_name: str) -> None:
        from google.cloud import storage  # type: ignore[import]

        self._bucket_name = bucket_name
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> StoredFile:
        """Upload bytes to GCS under ``key``.

        Args:
            key: GCS object name (e.g. ``music/lyria/2025-01-01/abc.mp3``)
            data: Raw bytes to store
            content_type: MIME type

        Returns:
            StoredFile with ``url=/files/{key}``
        """
        blob = self._bucket.blob(key)
        await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type)
        logger.info("GCS upload: bucket=%s key=%s size=%d", self._bucket_name, key, len(data))
        return StoredFile(
            key=key,
            url=f"/files/{key}",
            size_bytes=len(data),
            content_type=content_type,
        )

    async def download(self, key: str) -> bytes:
        """Download bytes from GCS.

        Raises:
            FileNotFoundError: If the object does not exist.
        """
        blob = self._bucket.blob(key)
        exists = await asyncio.to_thread(blob.exists)
        if not exists:
            raise FileNotFoundError(f"GCS object not found: gs://{self._bucket_name}/{key}")
        return await asyncio.to_thread(blob.download_as_bytes)  # type: ignore[return-value]

    async def delete(self, key: str) -> bool:
        """Delete a GCS object.

        Returns:
            True if deleted, False if the object did not exist.
        """
        blob = self._bucket.blob(key)
        exists = await asyncio.to_thread(blob.exists)
        if not exists:
            return False
        await asyncio.to_thread(blob.delete)
        return True

    async def get_url(self, key: str, expires_in: int = 3600) -> str:  # noqa: ARG002
        """Return the proxy URL for this key.

        Note: We intentionally return ``/files/{key}`` (not a signed GCS URL)
        so that all access goes through the backend proxy, which keeps the bucket private.
        """
        return f"/files/{key}"

    async def exists(self, key: str) -> bool:
        """Check whether a GCS object exists."""
        blob = self._bucket.blob(key)
        return await asyncio.to_thread(blob.exists)  # type: ignore[return-value]
