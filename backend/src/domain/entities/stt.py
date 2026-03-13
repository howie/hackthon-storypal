"""STT (Speech-to-Text) domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.entities.audio import AudioData


@dataclass(frozen=True)
class WordTiming:
    """Word-level timing information."""

    word: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0
    speaker_id: str | None = None

    @property
    def duration_ms(self) -> int:
        """Get word duration in milliseconds."""
        return self.end_ms - self.start_ms


@dataclass(frozen=True)
class SpeakerSegment:
    """A contiguous speech segment from a single speaker."""

    speaker_id: str
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class STTRequest:
    """Request for STT transcription - immutable value object."""

    provider: str
    language: str = "zh-TW"
    audio: AudioData | None = None
    audio_url: str | None = None
    enable_word_timing: bool = True
    child_mode: bool = False
    age_group: str | None = None
    enable_diarization: bool = False

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if self.audio is None and self.audio_url is None:
            raise ValueError("Either audio or audio_url must be provided")
        if self.age_group is not None and self.age_group not in ("2-4", "5-7", "8-12"):
            raise ValueError(
                f"Invalid age_group: {self.age_group}. Must be '2-4', '5-7', or '8-12'"
            )
        if self.age_group is not None and not self.child_mode:
            object.__setattr__(self, "child_mode", True)


@dataclass
class STTResult:
    """Result of STT transcription."""

    request: STTRequest
    transcript: str
    confidence: float | None
    latency_ms: int
    words: list[WordTiming] = field(default_factory=list)
    speaker_segments: list[SpeakerSegment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def provider(self) -> str:
        """Get provider name from request."""
        return self.request.provider

    @property
    def language(self) -> str:
        """Get language from request."""
        return self.request.language

    @property
    def audio_duration_ms(self) -> int | None:
        """Get audio duration in milliseconds from metadata."""
        return self.metadata.get("audio_duration_ms")

    @property
    def word_count(self) -> int:
        """Get word count of transcript."""
        return len(self.transcript.split())
