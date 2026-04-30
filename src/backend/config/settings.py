import os
from pathlib import Path
from typing import Any

from codex_core.settings import BaseCommonSettings
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict

# Root directory of the project
BASE_DIR = Path(__file__).parent.parent.parent.parent


class BackendSettings(BaseCommonSettings):
    """Backend-specific settings for game logic and events."""

    debug: bool = True

    # Server Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    # Auth / persistence
    site_database_url: str = (
        "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_site"  # pragma: allowlist secret
    )
    game_database_url: str = (
        "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_game"  # pragma: allowlist secret
    )
    database_url: str = site_database_url
    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Event Streams
    game_stream_name: str = "game_events"
    stream_consumer_group: str = "monolith"
    worker_name: str = "worker_1"
    stream_enabled_groups: list[str] | None = None  # None means all groups (monolith mode)

    @field_validator("stream_enabled_groups", mode="before")
    @classmethod
    def parse_csv_groups(cls, v: Any) -> list[str] | None:
        if isinstance(v, str) and v:
            return [s.strip() for s in v.split(",")]
        return v

    @model_validator(mode="after")
    def validate_consumer_group(self) -> "BackendSettings":
        if self.stream_enabled_groups and self.stream_consumer_group == "monolith":
            raise ValueError("Partial enabled_groups cannot use 'monolith' consumer group")
        return self

    world_auto_generate: bool = False
    world_generation_mode: str = "test"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def effective_redis_url(self) -> str:
        return os.getenv("REDIS_URL") or self.redis_url


settings = BackendSettings()
