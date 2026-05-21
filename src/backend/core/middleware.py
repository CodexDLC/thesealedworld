from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.backend.core.arq import SYSTEM_ARQ_QUEUE, ArqService

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response


class ActiveCharacterDirtySyncMiddleware(BaseHTTPMiddleware):
    """Queues a fire-and-forget AC persistence task for the current request character."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        char_id = self._request_char_id(request)
        if char_id is None:
            return response

        character_sessions = getattr(request.app.state, "character_sessions", None)
        if character_sessions is None:
            logger.bind(char_id=char_id).warning("ActiveCharacterDirtySyncSkipped")
            return response

        try:
            is_dirty = await character_sessions.is_dirty(char_id)
        except Exception:  # noqa: BLE001
            logger.bind(char_id=char_id).exception("ActiveCharacterDirtySyncCheckFailed")
            return response

        if not is_dirty:
            return response

        await self._enqueue_sync_request(request, char_id)
        return response

    async def _enqueue_sync_request(self, request: Request, char_id: int) -> None:
        arq = await self._system_arq(request)
        if arq is None:
            return

        try:
            await arq.enqueue_job(
                "sync_active_session_task",
                {
                    "char_id": char_id,
                    "source": "ac_dirty_middleware",
                },
            )
        except Exception:  # noqa: BLE001
            logger.bind(char_id=char_id).exception("ActiveCharacterDirtySyncEnqueueFailed")

    async def _system_arq(self, request: Request) -> Any | None:
        arq = getattr(request.app.state, "system_arq", None)
        if arq is not None:
            return arq

        try:
            arq = ArqService(queue_name=SYSTEM_ARQ_QUEUE)
        except Exception:  # noqa: BLE001
            logger.exception("ActiveCharacterDirtySyncSystemArqUnavailable")
            return None

        request.app.state.system_arq = arq
        return arq

    @staticmethod
    def _request_char_id(request: Request) -> int | None:
        path_params = getattr(request, "path_params", {})
        query_params = getattr(request, "query_params", {})

        for key in ("char_id", "character_id"):
            raw = path_params.get(key) if hasattr(path_params, "get") else None
            if raw is None and hasattr(query_params, "get"):
                raw = query_params.get(key)
            if raw is None:
                continue
            try:
                return int(raw)
            except (TypeError, ValueError):
                logger.bind(param=key, value=raw).warning("ActiveCharacterDirtySyncInvalidCharacterId")
                return None

        return None
