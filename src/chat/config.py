import os

from codex_core.settings import BaseCommonSettings
from pydantic_settings import SettingsConfigDict


class ChatSettings(BaseCommonSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "0.0.0.0"  # nosec
    app_port: int = 8002

    database_url: str = (
        "postgresql+asyncpg://tbmmorpg:tbmmorpg_dev@127.0.0.1:5432/tbmmorpg_site"  # pragma: allowlist secret
    )
    database_echo: bool = False

    secret_key: str = "change-me-in-env-change-me-in-env-32-bytes"  # pragma: allowlist secret
    access_token_expire_minutes: int = 30

    # Redis Streams (shared with backend)
    game_stream_name: str = "game_events"
    game_stream_maxlen: int = 10_000
    stream_consumer_group: str = "chat"
    worker_name: str = "chat_worker_1"

    @property
    def effective_redis_url(self) -> str:
        return os.getenv("REDIS_URL") or self.redis_url

    # Chat buffer settings
    chat_buffer_maxlen: int = 5_000
    chat_history_tail: int = 50


settings = ChatSettings()
