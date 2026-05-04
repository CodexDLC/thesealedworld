from codex_core.common.loguru_setup import setup_logging as codex_setup_logging
from codex_core.settings import BaseCommonSettings


def setup_logging(
    settings: BaseCommonSettings,
    service_name: str,
    intercept_loggers: list[str] | None = None,
    log_levels: dict[str, int] | None = None,
) -> None:
    """Configure Loguru via codex_core for any service (backend, frontend, workers)."""
    codex_setup_logging(
        settings=settings,  # type: ignore[arg-type]
        service_name=service_name,
        intercept_loggers=intercept_loggers or [],
        log_levels=log_levels or {},
    )
