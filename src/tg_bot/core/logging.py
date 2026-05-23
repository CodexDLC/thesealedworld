from typing import TYPE_CHECKING, cast

from src.shared.infrastructure.logging_config import setup_logging as shared_setup_logging

from .config import BotSettings

if TYPE_CHECKING:
    from src.shared.infrastructure.logging_config import BaseCommonSettings

TG_BOT_INTERCEPT_LOGGERS = [
    "aiogram",
    "aiogram.dispatcher",
    "aiogram.event",
    "aiogram.middlewares",
    "aiogram.scene",
    "codex_bot",
    "httpx",
    "httpcore",
    "redis",
    "redis.asyncio",
]


def setup_logging(settings: BotSettings) -> None:
    shared_setup_logging(
        settings=cast("BaseCommonSettings", settings),
        service_name="tg-bot",
        intercept_loggers=TG_BOT_INTERCEPT_LOGGERS,
        log_levels={
            "aiogram": 30,
            "aiogram.dispatcher": 30,
            "aiogram.event": 30,
            "aiogram.middlewares": 30,
            "aiogram.scene": 30,
            "codex_bot": 30,
            "httpx": 30,
            "httpcore": 30,
            "redis": 30,
            "redis.asyncio": 30,
        },
    )
