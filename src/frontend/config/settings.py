from pathlib import Path
from typing import Literal

from codex_core.settings import BaseCommonSettings
from pydantic_settings import SettingsConfigDict

# Root directory of the project
BASE_DIR = Path(__file__).parent.parent.parent.parent


class FrontendSettings(BaseCommonSettings):
    """Frontend-specific settings inheriting from codex-core base."""

    # Logging
    debug: bool = True
    log_level_console: str = "DEBUG"
    log_level_file: str = "INFO"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # Server Settings
    app_host: str = "0.0.0.0"  # nosec
    app_port: int = 8000
    backend_base_url: str = "http://127.0.0.1:8001"
    chat_ws_url: str = "ws://127.0.0.1:8002"
    backend_internal_service_key: str = "dev-site-to-game-service-key"  # pragma: allowlist secret
    backend_internal_service_header: str = "X-Internal-Service-Key"
    active_character_cookie_secure: bool = False
    game_token_cookie_secure: bool = False
    auth_user_cache_ttl_seconds: int = 30 * 60
    site_database_url: str = (
        "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_site"  # pragma: allowlist secret
    )
    database_url: str = site_database_url
    database_echo: bool = False
    secret_key: str = "change-me-in-env-change-me-in-env-32-bytes"  # pragma: allowlist secret
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    authx_jwt_algorithm: str = "HS256"
    authx_jwt_token_locations: list[str] = ["headers"]
    default_symbiote_name: str = "SYSTEM"
    enable_dev_rift_routes: bool = True

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_start_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@thesealed.world"
    email_admin: str = "primecodex@gmail.com"

    # SEO / Analytics
    site_name: str = "The Sealed World"
    site_base_url: str = ""
    site_meta_title: str = "The Sealed World"
    site_meta_description: str = (
        "Browser-based turn-based MMORPG about dangerous expeditions beyond the wall, loot, and making it home alive."
    )
    site_meta_image: str = "/static/images/site/the-sealed-world/hero-main.webp"
    google_tag_manager_id: str = ""
    google_analytics_id: str = ""
    google_site_verification: str = ""

    # Paths
    templates_dir: Path = BASE_DIR / "src" / "frontend" / "templates"
    static_dir: Path = BASE_DIR / "src" / "frontend" / "static"
    generated_assets_dir: Path = BASE_DIR / "var" / "generated-assets"

    # Generated asset serving. S3 keeps the public URL contract at /static/generated-assets/<storage_key>.
    asset_storage_backend: Literal["local", "s3"] = "local"
    asset_public_base_url: str = "/static/generated-assets"
    asset_local_root: str = "var/generated-assets"
    asset_s3_bucket: str | None = None
    asset_s3_region: str | None = None
    asset_s3_endpoint_url: str | None = None
    asset_s3_access_key_id: str | None = None
    asset_s3_secret_access_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = FrontendSettings()
