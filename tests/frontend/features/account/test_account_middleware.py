from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import Response

from src.frontend.features.account.middleware.account_auth import AccountAuthMiddleware


def _request_for_path(path: str, *, user=None):
    scope = {"type": "http", "method": "GET", "path": path, "query_string": b"", "headers": []}
    request = MagicMock()
    request.url.path = path
    request.state = SimpleNamespace(user=user)
    return request


@pytest.mark.unit
class TestAccountAuthMiddleware:
    @pytest.fixture
    def middleware(self):
        return AccountAuthMiddleware(app=SimpleNamespace())

    async def test_blocks_anonymous_users(self, middleware):
        request = _request_for_path("/account/profile")
        call_next = AsyncMock(return_value=Response("ok"))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        call_next.assert_not_called()

    async def test_blocks_anonymous_on_account_root(self, middleware):
        request = _request_for_path("/account")
        call_next = AsyncMock(return_value=Response("ok"))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 303
        assert response.headers["location"] == "/login"

    async def test_allows_authenticated_users(self, middleware):
        user = MagicMock()
        request = _request_for_path("/account/profile", user=user)
        call_next = AsyncMock(return_value=Response("ok"))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()

    async def test_ignores_non_account_paths(self, middleware):
        request = _request_for_path("/login")
        call_next = AsyncMock(return_value=Response("ok"))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()
