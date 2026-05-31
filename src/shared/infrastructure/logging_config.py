import logging
import os
import socket

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


def _runtime_instance_name() -> str | None:
    for env_name in ("CONTAINER_NAME", "HOSTNAME", "COMPUTERNAME"):
        value = os.getenv(env_name, "").strip()
        if value:
            return value

    hostname = socket.gethostname().strip()
    return hostname or None


def _service_name_with_runtime_instance(service_name: str, include_runtime_instance: bool) -> str:
    if not include_runtime_instance:
        return service_name

    instance_name = _runtime_instance_name()
    if not instance_name or instance_name == service_name:
        return service_name

    return f"{service_name}@{instance_name}"


def setup_logging(
    settings: BaseCommonSettings,
    service_name: str,
    intercept_loggers: list[str] | None = None,
    log_levels: dict[str, int] | None = None,
    include_runtime_instance: bool = False,
) -> None:
    """Configure Loguru via codex_core for any service (backend, frontend, workers)."""
    effective_log_levels = {**DEFAULT_NOISY_LOG_LEVELS, **(log_levels or {})}
    codex_setup_logging(
        settings=settings,  # type: ignore[arg-type]
        service_name=_service_name_with_runtime_instance(service_name, include_runtime_instance),
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
