from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.frontend.features.auth.dto.token import Token
from src.frontend.features.auth.dto.user import UserResponse
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.features.auth.services.site_auth_service import (
    RefreshTokenExpiredError,
    RefreshTokenNotFoundError,
)
from src.shared.exceptions import AuthException


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


@pytest.mark.asyncio
async def test_login_raises_auth_exception_for_bad_credentials() -> None:
    site_auth = SimpleNamespace(authenticate_user=AsyncMock(return_value=None))
    service = FrontendAuthService(auth_service=site_auth)

    with pytest.raises(AuthException):
        await service.login("player@example.com", "bad")


@pytest.mark.asyncio
async def test_login_creates_tokens_for_valid_user() -> None:
    tokens = Token(access_token="access", refresh_token="refresh")
    site_auth = SimpleNamespace(
        authenticate_user=AsyncMock(return_value=_user()),
        create_tokens=AsyncMock(return_value=tokens),
    )
    service = FrontendAuthService(auth_service=site_auth)

    assert await service.login("player@example.com", "password") == tokens


@pytest.mark.asyncio
async def test_get_current_user_uses_refresh_cookie_when_access_cookie_missing(mocker) -> None:
    mocker.patch(
        "src.frontend.features.auth.services.auth_service.decode_access_token",
        return_value={"sub": "00000000-0000-0000-0000-000000000001"},
    )
    tokens = Token(access_token="new_access", refresh_token="new_refresh")
    site_auth = SimpleNamespace(
        refresh_token=AsyncMock(return_value=tokens),
        get_user_by_id=AsyncMock(return_value=_user()),
    )
    service = FrontendAuthService(auth_service=site_auth)
    request = _request(refresh_token="old_refresh")

    user = await service.get_current_user(request)

    assert user == _user()
    site_auth.refresh_token.assert_awaited_once_with("old_refresh")
    assert request.state.access_token == "new_access"
    assert request.state.auth_tokens.refresh_token == "new_refresh"


@pytest.mark.asyncio
async def test_refresh_token_not_found_does_not_clear_cookies(mocker) -> None:
    """Rotation race: sibling request rotated the cookie.

    The losing request must NOT mark cookies for clearing — it would force a
    silent logout. Instead the request stays anonymous and the next render
    cycle either succeeds with the freshly issued cookie or falls into the
    hard-fail branch below.
    """
    mocker.patch(
        "src.frontend.features.auth.services.auth_service.decode_access_token",
        side_effect=ValueError("Token expired"),
    )
    site_auth = SimpleNamespace(
        refresh_token=AsyncMock(side_effect=RefreshTokenNotFoundError("Invalid refresh token")),
        get_user_by_id=AsyncMock(),
    )
    service = FrontendAuthService(auth_service=site_auth)
    request = _request(access_token="stale", refresh_token="lost-in-race")

    user = await service.get_current_user(request)

    assert user is None
    assert not getattr(request.state, "clear_auth_cookies", False)


@pytest.mark.asyncio
async def test_refresh_token_expired_clears_cookies(mocker) -> None:
    """Hard fail: refresh token actually expired — logout must propagate."""
    mocker.patch(
        "src.frontend.features.auth.services.auth_service.decode_access_token",
        side_effect=ValueError("Token expired"),
    )
    site_auth = SimpleNamespace(
        refresh_token=AsyncMock(side_effect=RefreshTokenExpiredError("Refresh token expired")),
        get_user_by_id=AsyncMock(),
    )
    service = FrontendAuthService(auth_service=site_auth)
    request = _request(access_token="stale", refresh_token="really-expired")

    user = await service.get_current_user(request)

    assert user is None
    assert request.state.clear_auth_cookies is True


@pytest.mark.asyncio
async def test_get_current_user_refreshes_when_access_cookie_is_expired(mocker) -> None:
    decode = mocker.patch(
        "src.frontend.features.auth.services.auth_service.decode_access_token",
        side_effect=[
            ValueError("Token expired"),
            {"sub": "00000000-0000-0000-0000-000000000001"},
        ],
    )
    tokens = Token(access_token="new_access", refresh_token="new_refresh")
    site_auth = SimpleNamespace(
        refresh_token=AsyncMock(return_value=tokens),
        get_user_by_id=AsyncMock(return_value=_user()),
    )
    service = FrontendAuthService(auth_service=site_auth)
    request = _request(access_token="old_access", refresh_token="old_refresh")

    user = await service.get_current_user(request)

    assert user == _user()
    assert decode.call_count == 2
    site_auth.refresh_token.assert_awaited_once_with("old_refresh")
    assert request.state.access_token == "new_access"
    assert request.state.auth_tokens.refresh_token == "new_refresh"
