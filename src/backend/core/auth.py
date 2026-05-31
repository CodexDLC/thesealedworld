import uuid
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from src.backend.core.exceptions import AuthException, PermissionDeniedException, SessionReplacedException
from src.backend.core.game_auth import GameTokenClaims, decode_game_access_token
from src.backend.core.security import decode_access_token
from src.shared.schemas.auth import AuthenticatedUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/game-lobby/select")
User = AuthenticatedUser


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> AuthenticatedUser:
    if _looks_like_game_token(token):
        claims = decode_game_access_token(token)
        await _enforce_single_game_session(request, claims)
        request.state.game_token_claims = claims
        return AuthenticatedUser(id=claims.sub, is_active=True, is_superuser=False)

    try:
        payload = decode_access_token(token)
        user_id_raw: Any = payload.get("sub")
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, TypeError) as exc:
        raise AuthException(detail="Could not validate credentials") from exc

    return AuthenticatedUser(
        id=user_id,
        email=payload.get("email"),
        is_active=True,
        is_superuser=False,
    )


async def _enforce_single_game_session(request: Request, claims: GameTokenClaims) -> None:
    """Reject game-token requests whose session id was replaced by another login.

    Tokens issued before single-session enforcement carried ``session_id=str(char_id)``
    (or no session_id at all); when the production lock manager is wired in, the
    check below treats any mismatch with the claimed slot for ``character_id`` as a
    replaced session and raises ``SessionReplacedException`` (HTTP 409 +
    ``HX-Trigger: session-replaced``). Stripped test setups without an attached
    app/state simply skip the check.
    """
    app = getattr(request, "app", None)
    state = getattr(app, "state", None) if app is not None else None
    lock = getattr(state, "game_session_lock", None) if state is not None else None
    if lock is None:
        return
    if not claims.session_id:
        raise AuthException(detail="Game token has no session id; please re-enter the lobby")
    current = await lock.current(claims.character_id)
    if current != claims.session_id:
        raise SessionReplacedException()


def require_game_character_scope(request: Request, user: AuthenticatedUser, character_id: int) -> None:
    claims: GameTokenClaims | None = getattr(request.state, "game_token_claims", None)
    if claims is None:
        return
    if claims.sub != user.id or claims.character_id != character_id:
        raise PermissionDeniedException("Game token does not match requested character")


def _looks_like_game_token(token: str) -> bool:
    try:
        _, payload_raw, _ = token.split(".")
        import base64
        import json

        padding = "=" * (-len(payload_raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_raw + padding))
    except Exception:
        return False
    token_type = payload.get("token_type")
    return token_type in {"game_access", "game_refresh"}
