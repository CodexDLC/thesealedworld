from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from src.frontend.integrations.backend_api.auth import TokenResponse, UserResponse
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService


def _request(*, access_token: str | None = None, refresh_token: str | None = None):
    cookies = {}
    if access_token:
        cookies["tbmmorpg_access_token"] = access_token
    if refresh_token:
        cookies["tbmmorpg_refresh_token"] = refresh_token
    return SimpleNamespace(cookies=cookies, state=SimpleNamespace())


def _user() -> UserResponse:
    return UserResponse(
        id="00000000-0000-0000-0000-000000000001",
        email="player@example.com",
        is_active=True,
        is_superuser=False,
        created_at="2026-05-02T00:00:00",
    )


def _unauthorized() -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://backend/auth/me")
    response = httpx.Response(401, request=request)
    return httpx.HTTPStatusError("Unauthorized", request=request, response=response)


@pytest.mark.asyncio
async def test_get_current_user_refreshes_expired_access_token() -> None:
    api = SimpleNamespace(
        current_user=AsyncMock(side_effect=[_unauthorized(), _user()]),
        refresh=AsyncMock(return_value=TokenResponse(access_token="new_access", refresh_token="new_refresh")),
    )
    service = FrontendAuthService(auth_api=api)
    request = _request(access_token="old_access", refresh_token="old_refresh")

    user = await service.get_current_user(request)

    assert user == _user()
    api.refresh.assert_awaited_once_with("old_refresh")
    assert request.state.access_token == "new_access"
    assert request.state.auth_tokens.refresh_token == "new_refresh"
    assert api.current_user.await_args_list[1].args == ("new_access",)


@pytest.mark.asyncio
async def test_get_current_user_uses_refresh_cookie_when_access_cookie_missing() -> None:
    api = SimpleNamespace(
        current_user=AsyncMock(return_value=_user()),
        refresh=AsyncMock(return_value=TokenResponse(access_token="new_access", refresh_token="new_refresh")),
    )
    service = FrontendAuthService(auth_api=api)
    request = _request(refresh_token="old_refresh")

    user = await service.get_current_user(request)

    assert user == _user()
    api.refresh.assert_awaited_once_with("old_refresh")
    api.current_user.assert_awaited_once_with("new_access")
