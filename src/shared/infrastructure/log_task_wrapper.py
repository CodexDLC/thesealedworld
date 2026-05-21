"""Decorator for ARQ worker tasks that injects structured log context.

Wraps each task invocation with a unique ``request_id``, ``task_name``,
and any domain IDs found in the first positional argument (if it is a dict).
"""

import functools
import uuid
from typing import Any

from codex_core.common.log_context import clear_log_context, set_log_context

_PAYLOAD_ID_KEYS = ("char_id", "combat_id", "session_id", "correlation_id")


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
        try:
            return await func(ctx, *args, **kwargs)
        finally:
            clear_log_context()

    return wrapper
