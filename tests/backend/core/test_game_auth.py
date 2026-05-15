from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.backend.config.settings import settings
from src.backend.core.auth import get_current_user, require_game_character_scope
from src.backend.core.exceptions import AuthException, PermissionDeniedException
from src.backend.core.game_auth import (
    create_game_access_token,
    create_game_refresh_token,
    decode_game_access_token,
    decode_game_refresh_token,
    refresh_game_token_pair,
    require_internal_service_key,
)


@pytest.mark.unit
def test_game_access_token_encode_decode() -> None:
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42, session_id="session-42")

    claims = decode_game_access_token(token)

    assert claims.token_type == "game_access"
    assert claims.sub == user_id
    assert claims.character_id == 42
    assert claims.session_id == "session-42"


@pytest.mark.unit
def test_game_refresh_token_rotates_pair() -> None:
    user_id = uuid4()
    refresh = create_game_refresh_token(user_id=user_id, character_id=42, session_id="session-42")

    pair = refresh_game_token_pair(refresh)
    access_claims = decode_game_access_token(pair.access_token)
    refresh_claims = decode_game_refresh_token(pair.refresh_token or "")

    assert access_claims.sub == user_id
    assert refresh_claims.character_id == 42


@pytest.mark.unit
def test_game_token_rejects_wrong_token_type() -> None:
    token = create_game_refresh_token(user_id=uuid4(), character_id=42)

    with pytest.raises(AuthException, match="Invalid game token type"):
        decode_game_access_token(token)


@pytest.mark.unit
def test_game_token_rejects_expired_token() -> None:
    token = create_game_access_token(user_id=uuid4(), character_id=42, expires_delta=timedelta(seconds=-1))

    with pytest.raises(AuthException, match="Game token expired"):
        decode_game_access_token(token)


@pytest.mark.unit
async def test_internal_service_key_missing_or_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "site_to_game_service_key", "expected-key")
    monkeypatch.setattr(settings, "frontend_internal_service_key", None)

    with pytest.raises(PermissionDeniedException, match="Invalid internal service key"):
        await require_internal_service_key(None)

    with pytest.raises(PermissionDeniedException, match="Invalid internal service key"):
        await require_internal_service_key("wrong-key")

    identity = await require_internal_service_key("expected-key")
    assert identity.name == "frontend-site"


@pytest.mark.unit
async def test_get_current_user_accepts_game_access_token() -> None:
    user_id = uuid4()
    token = create_game_access_token(user_id=user_id, character_id=42)
    request = SimpleNamespace(state=SimpleNamespace())

    user = await get_current_user(request, token)

    assert user.id == user_id
    assert request.state.game_token_claims.character_id == 42


@pytest.mark.unit
def test_game_character_scope_rejects_mismatched_character() -> None:
    user_id = uuid4()
    request = SimpleNamespace(
        state=SimpleNamespace(game_token_claims=decode_game_access_token(create_game_access_token(user_id=user_id, character_id=42)))
    )
    user = SimpleNamespace(id=user_id)

    with pytest.raises(PermissionDeniedException, match="does not match requested character"):
        require_game_character_scope(request, user, 43)
