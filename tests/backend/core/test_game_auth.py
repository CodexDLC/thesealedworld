from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.backend.config.settings import settings
from src.backend.core.auth import _looks_like_game_token, get_current_user, require_game_character_scope
from src.backend.core.exceptions import AuthException, PermissionDeniedException
from src.backend.core.game_auth import (
    GAME_TOKEN_AUDIENCE,
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
def test_game_token_carries_audience_claim() -> None:
    """Audience pins the token to the game domain so a site-issued JWT signed
    with the same SECRET_KEY can't pass as a game token."""
    import base64
    import json

    token = create_game_access_token(user_id=uuid4(), character_id=42, session_id="sess-1")
    _, payload_raw, _ = token.split(".")
    padding = "=" * (-len(payload_raw) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_raw + padding))
    assert payload["aud"] == GAME_TOKEN_AUDIENCE


@pytest.mark.unit
def test_decode_rejects_token_without_audience() -> None:
    """A hand-rolled JWT signed with the same SECRET_KEY but missing `aud`
    must be rejected — this is the exact attack the audience guard blocks."""
    import base64
    import hashlib
    import hmac
    import json
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    payload = {
        "token_type": "game_access",
        "sub": str(uuid4()),
        "character_id": 42,
        "session_id": "sess-1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        # NO `aud` claim — simulates a site-domain JWT smuggled into game decoder.
    }
    header = {"alg": "HS256", "typ": "JWT"}

    def b64(obj):
        raw = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    signing_input = f"{b64(header)}.{b64(payload)}"
    signature = hmac.new(settings.secret_key.encode(), signing_input.encode(), hashlib.sha256).digest()
    token = f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

    with pytest.raises(AuthException, match="Invalid game token audience"):
        decode_game_access_token(token)


@pytest.mark.unit
def test_looks_like_game_token_requires_audience() -> None:
    """Dispatch must not even attempt to decode a non-game token as a game one."""
    import base64
    import json

    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    # Game-shaped payload but wrong audience
    payload_wrong_aud = b64({"token_type": "game_access", "aud": "tbmmorpg:site"})
    assert _looks_like_game_token(f"hdr.{payload_wrong_aud}.sig") is False

    # Correct game token passes the check
    real_token = create_game_access_token(user_id=uuid4(), character_id=42, session_id="sess-1")
    assert _looks_like_game_token(real_token) is True


@pytest.mark.unit
def test_game_character_scope_rejects_mismatched_character() -> None:
    user_id = uuid4()
    request = SimpleNamespace(
        state=SimpleNamespace(game_token_claims=decode_game_access_token(create_game_access_token(user_id=user_id, character_id=42)))
    )
    user = SimpleNamespace(id=user_id)

    with pytest.raises(PermissionDeniedException, match="does not match requested character"):
        require_game_character_scope(request, user, 43)
