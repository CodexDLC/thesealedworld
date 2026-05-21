import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from .config import BotSettings

if TYPE_CHECKING:
    from types import FrameType


def mask_sensitive_data(text: str) -> str:
    """Masks sensitive data in text (phones, emails, secrets)."""
    if not isinstance(text, str):
        return text

    # 1. Mask phones
    phone_pattern = r"(\+?\d{1,3}[\s-]?\d{3})[\s-]?\d{3,}[\s-]?(\d{2,4})"
    text = re.sub(phone_pattern, r"\1 *** \2", text)

    # 2. Mask Emails
    email_pattern = r"([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
    text = re.sub(email_pattern, r"\1***@\2", text)

    # 3. Mask sensitive keys (password, token, secret, etc.)
    # We use a combined pattern to avoid Jinja2 double-brace issues
    keys = "password|token|secret|api_key|key|authorization|cookie|session_id"
    # Using concatenation to avoid '}}' interpreted as Jinja2 end tag
    sensitive_pattern = r"(?i)(" + keys + r")([\s:=(\"]*)([^\s,;}\"']{4,})"
    text = re.sub(sensitive_pattern, r"\1\2***", text)

    return text


def masking_patcher(record: Any) -> None:
    """Loguru patcher for automatic masking."""
    record["message"] = mask_sensitive_data(record["message"])


class InterceptHandler(logging.Handler):
    """Intercepts standard logging messages and redirects to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_logging(settings: BotSettings) -> None:
    """Configures professional logging with granular control and masking."""
    service_name = "tg_bot"

    # Reset default handlers
    logger.remove()

    # Apply global masking patcher
    logger.configure(patcher=masking_patcher)

    # Form paths
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file_debug = log_dir / "debug.log"
    log_file_errors = log_dir / "errors.json"

    # 1. Add Console Sink
    logger.add(
        sink=sys.stdout,
        level="DEBUG" if settings.debug else "INFO",
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            f"<magenta>{service_name}</magenta> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # 2. Add File Sinks
    logger.add(
        sink=str(log_file_debug),
        level="DEBUG",
        rotation="10 MB",
        compression="zip",
        format="{time} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.add(
        sink=str(log_file_errors),
        level="ERROR",
        serialize=True,
        rotation="1 week",
        compression="zip",
    )

    # 3. Intercept Granular Loggers
    granular_loggers = [
        "aiogram.dispatcher",
        "aiogram.event",
        "aiogram.middlewares",
        "aiogram.scene",
        "sqlalchemy.engine",
        "httpx",  # For HTTP client logging
        "httpcore",  # For lower-level HTTP connection logging
        "uvicorn",  # For uvicorn server logging
        "arq",
    ]

    # Standard logging bridge
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    for logger_name in granular_loggers:
        target_logger = logging.getLogger(logger_name)
        target_logger.handlers = [InterceptHandler()]
        target_logger.propagate = False

        if "aiogram" in logger_name:
            target_logger.setLevel(logging.INFO)  # Aiogram is too verbose on DEBUG
        else:
            target_logger.setLevel(logging.DEBUG)  # Set to DEBUG to see all messages from these loggers

    logger.info(f"Logging system initialized | mode={'DEBUG' if settings.debug else 'INFO'}")
