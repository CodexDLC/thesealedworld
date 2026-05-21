import logging

from codex_core.common.loguru_setup import setup_logging as codex_setup_logging
from codex_core.settings import BaseCommonSettings

WARNING = 30

DEFAULT_NOISY_LOG_LEVELS: dict[str, int] = {
    "asyncio": WARNING,
    "hpack": WARNING,
    "httpcore": WARNING,
    "httpcore._trace": WARNING,
    "httpx": WARNING,
    "python_multipart": WARNING,
    "python_multipart.multipart": WARNING,
}


def setup_logging(
    settings: BaseCommonSettings,
    service_name: str,
    intercept_loggers: list[str] | None = None,
    log_levels: dict[str, int] | None = None,
) -> None:
    """Configure Loguru via codex_core for any service (backend, frontend, workers)."""
    effective_log_levels = {**DEFAULT_NOISY_LOG_LEVELS, **(log_levels or {})}
    codex_setup_logging(
        settings=settings,  # type: ignore[arg-type]
        service_name=service_name,
        intercept_loggers=intercept_loggers or [],
        log_levels=effective_log_levels,
    )

    # Prevent duplicates: codex_core installs InterceptHandler on both the
    # root logger (via basicConfig) and each named logger.  Without
    # propagate=False the message is caught by the named handler AND
    # bubbles up to root — producing two identical log lines.
    if intercept_loggers:
        for name in intercept_loggers:
            logging.getLogger(name).propagate = False
