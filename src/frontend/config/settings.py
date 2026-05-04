from pathlib import Path

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
    active_character_cookie_secure: bool = False

    # Paths
    templates_dir: Path = BASE_DIR / "src" / "frontend" / "templates"
    static_dir: Path = BASE_DIR / "src" / "frontend" / "static"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = FrontendSettings()
