from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.backend.core.auth import get_current_user
from src.backend.core.exceptions import AuthException, SessionReplacedException
from src.backend.core.game_auth import create_game_access_token


class _StubLock:
    def __init__(self, *, returned: str | None) -> None:
        self.returned = returned
        self.calls: list[int] = []

    async def current(self, char_id: int) -> str | None:
        self.calls.append(char_id)
        return self.returned


def _build_request(lock: _StubLock | None) -> SimpleNamespace:
    """Mirror what FastAPI gives the dependency: request.app.state.game_session_lock."""
    state = SimpleNamespace(game_session_lock=lock) if lock is not None else SimpleNamespace()
    return SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace())


@pytest.mark.unit
async def test_get_current_user_accepts_matching_session_id() -> None:
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42, session_id="sess-1")
    lock = _StubLock(returned="sess-1")
    request = _build_request(lock)

    user = await get_current_user(request, token)

    assert user.id == user_id
    assert lock.calls == [42]


@pytest.mark.unit
async def test_get_current_user_rejects_stale_session_id_with_409() -> None:
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42, session_id="sess-old")
    request = _build_request(_StubLock(returned="sess-new"))

    with pytest.raises(SessionReplacedException):
        await get_current_user(request, token)


@pytest.mark.unit
async def test_get_current_user_rejects_legacy_token_without_session_id() -> None:
    """Tokens minted before single-session enforcement (no session_id) must force re-login."""
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42)  # session_id=None
    request = _build_request(_StubLock(returned="sess-new"))

    with pytest.raises(AuthException, match="Game token has no session id"):
        await get_current_user(request, token)


@pytest.mark.unit
async def test_get_current_user_rejects_when_lock_is_empty() -> None:
    """If the per-character lock was released (logout / TTL expiry), reject the request."""
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42, session_id="sess-1")
    request = _build_request(_StubLock(returned=None))

    with pytest.raises(SessionReplacedException):
        await get_current_user(request, token)


@pytest.mark.unit
async def test_get_current_user_skips_check_when_lock_manager_missing() -> None:
    """Stripped test setups without Redis must keep working — the check is a no-op."""
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42, session_id="sess-anything")
    request = _build_request(None)

    user = await get_current_user(request, token)

    assert user.id == user_id
