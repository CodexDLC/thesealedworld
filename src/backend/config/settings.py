import os
from pathlib import Path
from typing import Any, Literal

from codex_core.settings import BaseCommonSettings
from pydantic import field_validator, model_validator
from pydantic_settings import SettingsConfigDict

# Root directory of the project
BASE_DIR = Path(__file__).parent.parent.parent.parent
_BUNDLED_TRAINED_COMBAT_AI_POLICY = (
    Path(__file__).resolve().parents[1]
    / "features"
    / "combat"
    / "runtime"
    / "ai"
    / "policies"
    / "trained_g500_seed0.json"
)


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
    database_url: str = game_database_url
    database_echo: bool = False
    mongo_url: str = "mongodb://127.0.0.1:27017"
    mongo_database: str = "tbmmorpg_analytics"
    mongo_server_selection_timeout_ms: int = 5_000
    monster_migration_backfill_batch_size: int = 200
    monster_mongo_write_retry_attempts: int = 3
    secret_key: str = "change-me-in-env-change-me-in-env-32-bytes"  # pragma: allowlist secret
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    authx_jwt_algorithm: str = "HS256"
    authx_jwt_token_locations: list[Literal["headers", "cookies", "json", "query"]] = ["headers"]
    site_to_game_service_key: str = "change-me-site-to-game-service-key"  # pragma: allowlist secret
    frontend_internal_service_key: str | None = "dev-site-to-game-service-key"  # pragma: allowlist secret
    game_access_token_expire_minutes: int = 15
    game_refresh_token_expire_minutes: int = 12 * 60
    default_symbiote_name: str = "SYSTEM"
    enable_dev_rift_routes: bool = True

    # Realtime gateway (/ws/realtime)
    # Anti-CSWSH: handshake is accepted only when ``Origin`` matches this list.
    # Auth cookie is read from the WS handshake; query token is kept as a
    # fallback for diagnostics/tests only.
    realtime_allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://localhost:8003",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8003",
        "http://127.0.0.1:8080",
        "http://thesealed.localhost:8080",
        "http://play.thesealed.localhost:8080",
        "http://play.localhost:8080",
    ]
    realtime_ping_interval_seconds: float = 30.0
    realtime_ping_timeout_seconds: float = 120.0  # 4 missed pings -> close; survives Chrome background throttling

    # Event Streams
    game_stream_name: str = "game_events"
    game_stream_maxlen: int = 10_000
    stream_consumer_group: str = "monolith"
    worker_name: str = "worker_1"
    stream_enabled_groups: list[str] | None = None  # None means all groups (monolith mode)
    chat_buffer_maxlen: int = 5_000
    chat_history_tail: int = 50

    @field_validator("stream_enabled_groups", mode="before")
    @classmethod
    def parse_csv_groups(cls, v: Any) -> list[str] | None:
        if isinstance(v, str) and v:
            return [s.strip() for s in v.split(",")]
        return v

    @field_validator("realtime_allowed_origins", mode="before")
    @classmethod
    def parse_csv_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str) and v:
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @model_validator(mode="after")
    def validate_consumer_group(self) -> "BackendSettings":
        if self.stream_enabled_groups and self.stream_consumer_group == "monolith":
            raise ValueError("Partial enabled_groups cannot use 'monolith' consumer group")
        return self

    world_auto_generate: bool = False
    world_generation_mode: str = "test"
    bootstrap_content_materialization_enabled: bool = True
    bootstrap_ai_generation_enabled: bool = False

    # Generated asset storage. Local dev can serve a mirror of these keys; prod can map them to S3/CDN.
    asset_storage_backend: Literal["local", "s3"] = "local"
    asset_public_base_url: str = "/static/generated-assets"
    asset_local_root: str = "var/generated-assets"
    asset_s3_bucket: str | None = None
    asset_s3_region: str | None = None
    asset_s3_endpoint_url: str | None = None
    asset_s3_access_key_id: str | None = None
    asset_s3_secret_access_key: str | None = None

    # LLM Settings
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_image_model: str = "gemini-2.5-flash-image"
    gemini_monster_image_model: str = "gemini-2.5-flash-image"
    gemini_location_image_model: str = "gemini-2.5-flash-image"
    gemini_avatar_image_model: str = "gemini-2.5-flash-image"
    monster_clan_flavor_ai_interval_seconds: float = 30.0
    gemini_token: str | None = None
    openrouter_api_key: str | None = None
    combat_ai_policy_path: str | None = None
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


def apply_runtime_environment_overrides() -> None:
    """Export runtime-only settings consumed by lower-level modules.

    PolicyStore intentionally reads process env or explicit paths only, so
    tests and tools keep the bundled default unless the application process
    opts into a live policy at startup.
    """

    policy_path = settings.combat_ai_policy_path
    if not policy_path and _BUNDLED_TRAINED_COMBAT_AI_POLICY.exists():
        policy_path = str(_BUNDLED_TRAINED_COMBAT_AI_POLICY)
    if policy_path:
        os.environ.setdefault("COMBAT_AI_POLICY_PATH", policy_path)
