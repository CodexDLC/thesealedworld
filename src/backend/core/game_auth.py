from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import Header
from pydantic import BaseModel, ConfigDict

from src.backend.config.settings import settings
from src.backend.core.exceptions import AuthException, PermissionDeniedException

GameTokenType = Literal["game_access", "game_refresh"]

# Audience claim that pins this token to the game/realtime domain. The site
# auth path (authx) never sets `aud`, so without this check a site-issued JWT
# could pass as a game token (same SECRET_KEY, same HS256). The decode path
# rejects any payload whose `aud` is not exactly this value.
GAME_TOKEN_AUDIENCE = "tbmmorpg:game"  # nosec B105 - JWT audience marker, not a secret.


class GameTokenPairDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    refresh_expires_in: int | None = None


class GameTokenClaims(BaseModel):
    model_config = ConfigDict(extra="allow")

    token_type: GameTokenType
    sub: uuid.UUID
    character_id: int
    session_id: str | None = None
    aud: str | None = None
    exp: int
    iat: int
    jti: str | None = None


class GameTokenRefreshRequestDTO(BaseModel):
    refresh_token: str


@dataclass(frozen=True, slots=True)
class InternalServiceIdentity:
    name: str = "frontend-site"


def _service_key() -> str:
    return settings.frontend_internal_service_key or settings.site_to_game_service_key


async def require_internal_service_key(
    x_internal_service_key: str | None = Header(default=None, alias="X-Internal-Service-Key"),
) -> InternalServiceIdentity:
    configured = _service_key()
    if not configured or configured.startswith("change-me-"):
        raise PermissionDeniedException("Internal service key is not configured")
    if not x_internal_service_key or not secrets.compare_digest(x_internal_service_key, configured):
        raise PermissionDeniedException("Invalid internal service key")
    return InternalServiceIdentity()


def create_game_access_token(
    *,
    user_id: uuid.UUID,
    character_id: int,
    session_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    return _encode_game_token(
        token_type="game_access",  # nosec B106
        user_id=user_id,
        character_id=character_id,
        session_id=session_id,
        expires_delta=expires_delta or timedelta(minutes=settings.game_access_token_expire_minutes),
    )


def create_game_refresh_token(
    *,
    user_id: uuid.UUID,
    character_id: int,
    session_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    return _encode_game_token(
        token_type="game_refresh",  # nosec B106
        user_id=user_id,
        character_id=character_id,
        session_id=session_id,
        expires_delta=expires_delta or timedelta(minutes=settings.game_refresh_token_expire_minutes),
    )


def create_game_token_pair(*, user_id: uuid.UUID, character_id: int, session_id: str | None = None) -> GameTokenPairDTO:
    access_expires = timedelta(minutes=settings.game_access_token_expire_minutes)
    refresh_expires = timedelta(minutes=settings.game_refresh_token_expire_minutes)
    return GameTokenPairDTO(
        access_token=create_game_access_token(
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
            expires_delta=access_expires,
        ),
        expires_in=int(access_expires.total_seconds()),
        refresh_token=create_game_refresh_token(
            user_id=user_id,
            character_id=character_id,
            session_id=session_id,
            expires_delta=refresh_expires,
        ),
        refresh_expires_in=int(refresh_expires.total_seconds()),
    )


def decode_game_access_token(token: str) -> GameTokenClaims:
    return _decode_game_token(token, expected_type="game_access")


def decode_game_refresh_token(token: str) -> GameTokenClaims:
    return _decode_game_token(token, expected_type="game_refresh")


def refresh_game_token_pair(refresh_token: str) -> GameTokenPairDTO:
    claims = decode_game_refresh_token(refresh_token)
    return create_game_token_pair(user_id=claims.sub, character_id=claims.character_id, session_id=claims.session_id)


def _encode_game_token(
    *,
    token_type: GameTokenType,
    user_id: uuid.UUID,
    character_id: int,
    session_id: str | None,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "token_type": token_type,
        "sub": str(user_id),
        "character_id": character_id,
        "session_id": session_id,
        "aud": GAME_TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    header = {"alg": settings.authx_jwt_algorithm, "typ": "JWT"}
    if settings.authx_jwt_algorithm != "HS256":
        raise ValueError("Only HS256 game tokens are supported")
    signing_input = f"{_b64url_json(header)}.{_b64url_json(payload)}"
    signature = hmac.new(settings.secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def _decode_game_token(token: str, *, expected_type: GameTokenType) -> GameTokenClaims:
    try:
        header_raw, payload_raw, signature_raw = token.split(".")
    except ValueError as exc:
        raise AuthException("Malformed game token") from exc

    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    expected = hmac.new(settings.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(signature_raw)
    if not hmac.compare_digest(expected, actual):
        raise AuthException("Invalid game token signature")

    header = json.loads(_b64url_decode(header_raw))
    if header.get("alg") != "HS256":
        raise AuthException("Invalid game token algorithm")

    payload: dict[str, Any] = json.loads(_b64url_decode(payload_raw))
    claims = GameTokenClaims.model_validate(payload)
    # Audience guard: refuse any token (even one signed with the same
    # SECRET_KEY) that wasn't minted for the game domain. Without this, a
    # site-auth JWT could pass here as long as its payload happened to carry
    # token_type + character_id.
    if claims.aud != GAME_TOKEN_AUDIENCE:
        raise AuthException("Invalid game token audience")
    if claims.token_type != expected_type:
        raise AuthException("Invalid game token type")
    if datetime.now(UTC).timestamp() >= claims.exp:
        raise AuthException("Game token expired")
    return claims


def _b64url_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64url_encode(raw)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
