"""Decorator for ARQ worker tasks that injects structured log context.

Wraps each task invocation with a unique ``request_id``, ``task_name``,
and any domain IDs found in the first positional argument (if it is a dict).
"""

import asyncio
import functools
import re
import time
import uuid
from typing import Any

from codex_core.common.log_context import clear_log_context, set_log_context
from loguru import logger

_PAYLOAD_ID_KEYS = ("run_id", "char_id", "combat_id", "session_id", "correlation_id")


def _task_event_name(task_name: str, suffix: str) -> str:
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", task_name) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts) + suffix


def logged_task(func: Any) -> Any:
    @functools.wraps(func)
    async def wrapper(ctx: dict, *args: Any, **kwargs: Any) -> Any:
        task_ctx: dict[str, Any] = {
            "request_id": uuid.uuid4().hex,
            "task_name": func.__name__,
        }
        if args and isinstance(args[0], dict):
            for key in _PAYLOAD_ID_KEYS:
                if key in args[0]:
                    task_ctx[key] = args[0][key]

        set_log_context(**task_ctx)
        started_at = time.perf_counter()
        bound_logger = logger.bind(**task_ctx)
        bound_logger.info(_task_event_name(func.__name__, "Started"))
        try:
            result = await func(ctx, *args, **kwargs)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            bound_logger.bind(duration_ms=duration_ms, status="completed").info(
                _task_event_name(func.__name__, "Finished")
            )
            return result
        except asyncio.CancelledError:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            bound_logger.bind(duration_ms=duration_ms, status="cancelled").warning(
                _task_event_name(func.__name__, "Cancelled")
            )
            raise
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            bound_logger.bind(duration_ms=duration_ms, status="failed").exception(
                _task_event_name(func.__name__, "Failed")
            )
            raise
        finally:
            clear_log_context()

    return wrapper
