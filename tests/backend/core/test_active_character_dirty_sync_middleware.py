from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.responses import Response

from src.backend.core.arq import SYSTEM_ARQ_QUEUE
from src.backend.core.middleware import ActiveCharacterDirtySyncMiddleware


@pytest.mark.unit
async def test_dirty_sync_middleware_enqueues_current_character_only() -> None:
    character_sessions = SimpleNamespace(is_dirty=AsyncMock(return_value=True))
    system_arq = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(character_sessions=character_sessions, system_arq=system_arq)),
        path_params={"char_id": "7"},
        query_params={},
    )
    middleware = ActiveCharacterDirtySyncMiddleware(app=SimpleNamespace())

    response = await middleware.dispatch(request, _ok_response)

    assert response.status_code == 204
    character_sessions.is_dirty.assert_awaited_once_with(7)
    system_arq.enqueue_job.assert_awaited_once_with(
        "sync_active_session_task",
        {
            "char_id": 7,
            "source": "ac_dirty_middleware",
        },
    )


@pytest.mark.unit
async def test_dirty_sync_middleware_skips_when_request_has_no_character_id() -> None:
    character_sessions = SimpleNamespace(is_dirty=AsyncMock(return_value=True))
    system_arq = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(character_sessions=character_sessions, system_arq=system_arq)),
        path_params={},
        query_params={},
    )
    middleware = ActiveCharacterDirtySyncMiddleware(app=SimpleNamespace())

    await middleware.dispatch(request, _ok_response)

    character_sessions.is_dirty.assert_not_awaited()
    system_arq.enqueue_job.assert_not_awaited()


@pytest.mark.unit
async def test_dirty_sync_middleware_skips_clean_active_session() -> None:
    character_sessions = SimpleNamespace(is_dirty=AsyncMock(return_value=False))
    system_arq = SimpleNamespace(enqueue_job=AsyncMock())
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(character_sessions=character_sessions, system_arq=system_arq)),
        path_params={},
        query_params={"char_id": "7"},
    )
    middleware = ActiveCharacterDirtySyncMiddleware(app=SimpleNamespace())

    await middleware.dispatch(request, _ok_response)

    character_sessions.is_dirty.assert_awaited_once_with(7)
    system_arq.enqueue_job.assert_not_awaited()


@pytest.mark.unit
async def test_dirty_sync_middleware_creates_system_arq_when_missing(mocker) -> None:
    character_sessions = SimpleNamespace(is_dirty=AsyncMock(return_value=True))
    created_arq = SimpleNamespace(enqueue_job=AsyncMock())
    arq_factory = mocker.patch("src.backend.core.middleware.ArqService", return_value=created_arq)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(character_sessions=character_sessions)),
        path_params={"char_id": "7"},
        query_params={},
    )
    middleware = ActiveCharacterDirtySyncMiddleware(app=SimpleNamespace())

    await middleware.dispatch(request, _ok_response)

    arq_factory.assert_called_once_with(queue_name=SYSTEM_ARQ_QUEUE)
    created_arq.enqueue_job.assert_awaited_once_with(
        "sync_active_session_task",
        {
            "char_id": 7,
            "source": "ac_dirty_middleware",
        },
    )


async def _ok_response(_request: object) -> Response:
    return Response(status_code=204)
