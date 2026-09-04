from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from CARTOON_STUDIO_* variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CARTOON_STUDIO_",
        extra="ignore",
    )

    environment: str = "local"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://cartoon:cartoon@127.0.0.1:55433/cartoon_studio"
    storage_endpoint: str = "http://127.0.0.1:19000"
    storage_bucket: str = "cartoon-studio-local"
    api_title: str = "Cartoon Studio API"
    api_version: str = "0.1.0"
    demo_mode: bool = True
    event_heartbeat_seconds: int = Field(default=15, ge=5, le=60)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
