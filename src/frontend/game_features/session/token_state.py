from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, Response, status

from src.frontend.config.settings import settings
from src.frontend.features.auth.token_state import get_access_token

GAME_ACCESS_COOKIE_NAME = "tbmmorpg_game_access_token"
GAME_REFRESH_COOKIE_NAME = "tbmmorpg_game_refresh_token"


def get_game_access_token(request: Request, *, allow_site_fallback: bool = True) -> str | None:
    state = getattr(request, "state", None)
    token = getattr(state, "game_access_token", None) or request.cookies.get(GAME_ACCESS_COOKIE_NAME)
    if token:
        return token
    if allow_site_fallback:
        return get_access_token(request)
    return None


def require_game_access_token(request: Request, *, allow_site_fallback: bool = True) -> str:
    token = get_game_access_token(request, allow_site_fallback=allow_site_fallback)
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/game-lobby"})
    return token


def set_game_token_cookies(response: Response, *, access_token: str, refresh_token: str | None = None) -> None:
    domain = settings.auth_cookie_domain or None
    response.set_cookie(
        GAME_ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=settings.game_token_cookie_secure,
        samesite="lax",
        path="/",
        domain=domain,
    )
    if refresh_token:
        response.set_cookie(
            GAME_REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            secure=settings.game_token_cookie_secure,
            samesite="lax",
            path="/",
            domain=domain,
        )


def clear_game_token_cookies(response: Response) -> None:
    domain = settings.auth_cookie_domain or None
    for name in (GAME_ACCESS_COOKIE_NAME, GAME_REFRESH_COOKIE_NAME):
        response.delete_cookie(name, path="/", domain=domain)
        if domain:
            # Also expire any legacy host-only cookie left from before the
            # domain-scoped scheme. Without this the stale duplicate keeps being
            # read on the next request and the refresh-reject loop never breaks.
            response.delete_cookie(name, path="/")


def attach_game_tokens_from_backend_response(response: Response, backend_response: Any) -> None:
    tokens = extract_game_tokens(backend_response)
    if tokens is None:
        return
    set_game_token_cookies(
        response,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
    )


def extract_game_tokens(backend_response: Any) -> dict[str, str] | None:
    candidates = [
        backend_response,
        getattr(backend_response, "payload", None),
        _mapping_get(getattr(backend_response, "payload", None), "tokens"),
        _mapping_get(getattr(backend_response, "payload", None), "game_tokens"),
        _mapping_get(getattr(backend_response, "payload", None), "extra_data"),
        _mapping_get(_mapping_get(getattr(backend_response, "payload", None), "extra_data"), "tokens"),
        _mapping_get(_mapping_get(getattr(backend_response, "payload", None), "extra_data"), "game_tokens"),
    ]
    for candidate in candidates:
        mapping = _as_mapping(candidate)
        if not mapping:
            continue
        access_token = mapping.get("game_access_token") or mapping.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            continue
        refresh_token = mapping.get("game_refresh_token") or mapping.get("refresh_token")
        return {
            "access_token": access_token,
            **({"refresh_token": refresh_token} if isinstance(refresh_token, str) and refresh_token else {}),
        }
    return None


def _mapping_get(value: Any, key: str) -> Any:
    mapping = _as_mapping(value)
    return mapping.get(key) if mapping else None


def _as_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        data = value.model_dump(mode="json")
        return data if isinstance(data, dict) else None
    return None
