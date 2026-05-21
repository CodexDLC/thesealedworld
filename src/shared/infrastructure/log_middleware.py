"""HTTP request context middleware for structured logging.

Injects ``request_id``, ``char_id``, and ``healthcheck`` marker into the
async-local log context so every log call within the request automatically
carries these fields.
"""

import uuid

from codex_core.common.log_context import clear_log_context, set_log_context
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_HEALTHCHECK_PATHS = frozenset({"/health", "/", "/metrics"})


class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = uuid.uuid4().hex
        ctx: dict = {"request_id": request_id}

        if request.url.path in _HEALTHCHECK_PATHS:
            ctx["healthcheck"] = True

        char_id = request.path_params.get("char_id") or request.path_params.get("character_id")
        if char_id is not None:
            ctx["char_id"] = int(char_id)

        set_log_context(**ctx)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_log_context()
