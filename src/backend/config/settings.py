import os
from pathlib import Path
from typing import Any, Literal

from codex_core.settings import BaseCommonSettings
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict

# Root directory of the project
BASE_DIR = Path(__file__).parent.parent.parent.parent


class BackendSettings(BaseCommonSettings):
    """Backend-specific settings for game logic and events."""

    debug: bool = True
    log_level_console: str = "DEBUG"
    log_level_file: str = "DEBUG"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # Server Settings
    app_host: str = "0.0.0.0"  # nosec
    app_port: int = 8001

    # Auth / persistence
    site_database_url: str = (
        "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_site"  # pragma: allowlist secret
    )
    game_database_url: str = (
        "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_game"  # pragma: allowlist secret
    )
    database_url: str = site_database_url
    database_echo: bool = False
    secret_key: str = "change-me-in-env-change-me-in-env-32-bytes"  # pragma: allowlist secret
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    authx_jwt_algorithm: str = "HS256"
    authx_jwt_token_locations: list[Literal["headers", "cookies", "json", "query"]] = ["headers"]
    default_symbiote_name: str = "SYSTEM"

    # Event Streams
    game_stream_name: str = "game_events"
    game_stream_maxlen: int = 10_000
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
    monster_population_clans_per_context: int = 1

    # LLM Settings
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_models: list[str] = ["gemini-2.5-pro"]
    monster_clan_flavor_ai_interval_seconds: float = 30.0
    gemini_token: str | None = None
    openrouter_api_key: str | None = None
    # Removed: bug_report_channel_id (per user request)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def effective_redis_url(self) -> str:
        return os.getenv("REDIS_URL") or self.redis_url


settings = BackendSettings()
