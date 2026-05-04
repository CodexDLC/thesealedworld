from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем корень проекта
# shared/core/config.py -> core -> shared -> src -> ROOT
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE_PATH = ROOT_DIR / ".env"


class CommonSettings(BaseSettings):
    """
    Базовые настройки, общие для всех сервисов (Backend, Bot).
    Включает Redis, Логирование и общие пути.
    """

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_max_connections: int = 50
    redis_timeout: int = 5

    # --- Logging ---
    log_level_console: str = "DEBUG"
    log_level_file: str = "DEBUG"
    log_rotation: str = "10 MB"
    log_dir: str = "logs"

    # --- System ---
    system_user_id: int = 2_000_000_000

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    # Логи
    @property
    def log_file_debug(self) -> str:
        return f"{self.log_dir}/debug.log"

    @property
    def log_file_errors(self) -> str:
        return f"{self.log_dir}/errors.json"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",  # Игнорировать лишние поля (например, DB_URL в боте)
    )
