"""TTS Provider Implementations.

Simplified for StoryPal: only Gemini TTS provider.
"""

from src.infrastructure.providers.tts.factory import TTSProviderFactory
from src.infrastructure.providers.tts.gemini_tts import GeminiTTSProvider

__all__ = ["GeminiTTSProvider", "TTSProviderFactory"]
