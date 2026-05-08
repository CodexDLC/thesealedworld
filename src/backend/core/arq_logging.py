from __future__ import annotations

from src.backend.config.settings import settings
from src.shared.logging_config import setup_logging

ARQ_INTERCEPT_LOGGERS = [
    "arq",
    "arq.worker",
    "arq.connections",
    "arq.jobs",
    "arq.utils",
]


def setup_arq_worker_logging(service_name: str) -> None:
    setup_logging(
        settings=settings,
        service_name=service_name,
        intercept_loggers=ARQ_INTERCEPT_LOGGERS,
        log_levels={
            "arq": 30,
            "arq.worker": 30,
            "arq.connections": 30,
            "arq.jobs": 30,
            "arq.utils": 30,
            "redis": 30,
            "redis.asyncio": 30,
        },
    )
