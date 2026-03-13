"""Voice sync job domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class VoiceSyncStatus(Enum):
    """Voice sync job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VoiceSyncJob:
    """Voice synchronization job entity."""

    id: str
    providers: list[str]
    status: VoiceSyncStatus
    voices_synced: int = 0
    voices_deprecated: int = 0
    error_message: str | None = None
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    MAX_RETRIES: int = field(default=3, init=False, repr=False)

    @classmethod
    def create(cls, providers: list[str] | None = None) -> "VoiceSyncJob":
        """Create a new sync job."""
        return cls(
            id=str(uuid4()),
            providers=providers or [],
            status=VoiceSyncStatus.PENDING,
        )
