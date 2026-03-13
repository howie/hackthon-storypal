"""ConversationTurn entity.

Represents a single turn in a voice interaction conversation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class ConversationTurn:
    """A single conversation turn within an interaction session."""

    session_id: UUID
    turn_number: int
    started_at: datetime
    id: UUID = field(default_factory=uuid4)
    user_audio_path: str | None = None
    user_transcript: str | None = None
    ai_response_text: str | None = None
    ai_audio_path: str | None = None
    interrupted: bool = False
    ended_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def set_user_input(self, transcript: str) -> None:
        """Set the user's transcribed input."""
        self.user_transcript = transcript

    def set_ai_response(self, text: str, audio_path: str | None) -> None:
        """Set the AI response text and optional audio path."""
        self.ai_response_text = text
        self.ai_audio_path = audio_path

    def end(self, *, interrupted: bool = False) -> None:
        """Mark this turn as ended."""
        self.ended_at = datetime.utcnow()
        if interrupted:
            self.interrupted = True
