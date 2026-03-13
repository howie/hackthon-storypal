"""Audio configuration — ensure ffmpeg is available for pydub.

Uses static-ffmpeg (bundled pre-built binaries) which includes libmp3lame,
ensuring WAV→MP3 conversion works regardless of the system ffmpeg installation.

Call ``configure_ffmpeg()`` once at application startup — it is
idempotent and safe to call multiple times.
"""

import logging

logger = logging.getLogger(__name__)

_configured = False


def configure_ffmpeg() -> None:
    """Inject static-ffmpeg binaries into PATH so pydub can find them.

    Uses static-ffmpeg instead of system ffmpeg to guarantee libmp3lame
    support for MP3 encoding (system ffmpeg may lack this codec).
    """
    global _configured  # noqa: PLW0603
    if _configured:
        return

    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
        logger.info("Using static-ffmpeg (includes libmp3lame)")
    except Exception:
        logger.warning(
            "static-ffmpeg setup failed (binary download may have failed). "
            "Audio conversion features may not work."
        )

    _configured = True
