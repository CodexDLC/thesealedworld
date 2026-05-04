import json
from typing import Any

from pydantic import field_validator

from src.shared.core.config import CommonSettings


class BackendSettings(CommonSettings):
    """
    Настройки для Backend (API, Core).
    Включает БД, Безопасность, CORS и параметры FastAPI.
    """

    # --- FastAPI Info ---
    project_name: str = "Telegram Bot RPG API"
    api_v1_str: str = "/api/v1"
    debug: bool = False

    # --- Database ---
    database_url: str = ""  # Required: must be set via .env or environment
    test_database_url: str | None = None
    db_ssl_require: bool = True
    auto_migrate: bool = True

    # --- Security ---
    secret_key: str = ""  # Required: must be set via .env or environment
    access_token_expire_minutes: int = 30

    # --- CORS (Cross-Origin Resource Sharing) ---
    # Формат в .env: ALLOWED_ORIGINS=["http://localhost:3000", "https://mygame.com"]
    allowed_origins: list[str] | str = ["*"]

    # --- Game Logic ---
    system_char_id: int = 999

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> Any:
        """
        Парсит JSON-строку из .env в список.

        Args:
            v: Значение из .env (строка или список).

        Returns:
            list[str]: Список разрешенных доменов.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [v]
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    def _fix_postgres_url(self, url: str) -> str:
        """
        Принудительно ставит драйвер asyncpg для Postgres.

        Args:
            url: Исходная строка подключения.

        Returns:
            str: Исправленная строка подключения.
        """
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sqlalchemy_database_url(self) -> str:
        """Возвращает URL базы данных с правильным драйвером."""
        return self._fix_postgres_url(self.database_url)

    @property
    def sqlalchemy_test_database_url(self) -> str:
        """Возвращает URL тестовой базы данных с правильным драйвером."""
        url = self.test_database_url or self.database_url
        return self._fix_postgres_url(url)


# Создаем экземпляр настроек для использования в backend
settings = BackendSettings()
