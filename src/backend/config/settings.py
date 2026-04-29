from pathlib import Path

from codex_core.settings import BaseCommonSettings
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
    site_database_url: str = "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_site"
    game_database_url: str = "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_game"
    database_url: str = site_database_url
    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Event Streams
    game_stream_name: str = "game_events"
    monolith_group: str = "monolith_group"
    worker_name: str = "worker_1"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = BackendSettings()
