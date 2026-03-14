"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Application
    app_name: str = "StoryPal"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Authentication
    disable_auth: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8888

    # Database
    database_url: str = "postgresql+asyncpg://storypal:storypal_dev@localhost:5432/storypal_dev"

    # Storage
    storage_type: Literal["local", "gcs"] = "local"
    storage_path: str = "./storage"

    # Google Cloud
    google_application_credentials: str = ""
    gcp_project_id: str = ""

    # CORS
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="cors_origins",
    )

    # OAuth Domain Restriction
    allowed_domains_str: str = Field(default="", alias="allowed_domains")

    # Google OAuth
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # V2V Performance Feature Toggles
    v2v_lightweight_mode: bool = True
    v2v_ws_compression: bool = False
    v2v_batch_audio_upload: bool = True
    v2v_skip_latency_tracking: bool = False

    # Gemini model configuration
    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"

    # Gemini API Key
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "gemini_api_key",
            "google_ai_api_key",
            "google_api_key",
        ),
    )

    # Usage limits
    max_stories_per_user: int = 3
    max_chat_messages_per_session: int = 10
    admin_contact_info: str = ""

    # Gemini TTS configuration
    gemini_tts_model: str = "gemini-2.5-pro-preview-tts"
    gemini_tts_default_voice: str = "Kore"

    @property
    def allowed_domains(self) -> list[str]:
        """Parse allowed domains from comma-separated string."""
        v = self.allowed_domains_str
        if not v or v == "*":
            return []
        return [domain.strip().lower() for domain in v.split(",") if domain.strip()]

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
