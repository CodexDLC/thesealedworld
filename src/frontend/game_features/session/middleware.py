from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from src.frontend.config.settings import settings
from src.frontend.game_features.session.token_state import (
    GAME_ACCESS_COOKIE_NAME,
    GAME_REFRESH_COOKIE_NAME,
    clear_game_token_cookies,
    set_game_token_cookies,
)
from src.frontend.integrations.backend_api.game_lobby import BackendGameLobbyApi, GameTokenPair

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

GAME_TOKEN_REFRESH_GRACE_SECONDS = 60
GAME_TOKEN_REFRESH_PATH_PREFIXES = (
    "/game",
    "/api/game",
    "/scenario",
    "/combat",
    "/exploration",
    "/inventory",
    "/arena",
    "/city-services",
)


class GameTokenRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if _should_refresh_for_path(request.url.path):
            await self._refresh_if_needed(request)

        response = await call_next(request)
        tokens = getattr(request.state, "game_tokens", None)
        if isinstance(tokens, GameTokenPair):
            set_game_token_cookies(
                response,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
            )
        elif getattr(request.state, "clear_game_token_cookies", False) or _is_session_replaced_response(response):
            clear_game_token_cookies(response)
        return response

    async def _refresh_if_needed(self, request: Request) -> None:
        refresh_token = request.cookies.get(GAME_REFRESH_COOKIE_NAME)
        if not refresh_token:
            return

        access_token = request.cookies.get(GAME_ACCESS_COOKIE_NAME)
        if access_token and not _token_needs_refresh(access_token):
            request.state.game_access_token = access_token
            return

        try:
            api = BackendGameLobbyApi(
                client=request.app.state.backend_http_client,
                base_url=settings.backend_base_url,
            )
            tokens = await api.refresh_token(refresh_token)
        except httpx.HTTPStatusError as exc:
            # 4xx from backend means the token / session itself is bad — clear
            # the cookies so the next request gets a clean login redirect.
            # Everything else (502, timeout, connection refused) is transient:
            # leave the cookies alone so the next request retries with the
            # same refresh token instead of force-logging the player out.
            status_code = exc.response.status_code
            if 400 <= status_code < 500:
                logger.bind(status=status_code).warning("FrontendGameTokenRefreshRejected")
                request.state.clear_game_token_cookies = True
            else:
                logger.bind(status=status_code).warning("FrontendGameTokenRefreshUnavailable")
            return
        except (httpx.RequestError, ConnectionError, TimeoutError) as exc:
            # Pure network/transport failure -> backend unreachable, not auth.
            # Do NOT clear cookies; the next refresh attempt may succeed.
            logger.bind(error=str(exc)).warning("FrontendGameTokenRefreshUnavailable")
            return
        except Exception as exc:
            logger.bind(error=str(exc)).warning("FrontendGameTokenRefreshRejected")
            request.state.clear_game_token_cookies = True
            return

        request.state.game_access_token = tokens.access_token
        if tokens.refresh_token:
            request.state.game_refresh_token = tokens.refresh_token
        request.state.game_tokens = tokens
        logger.debug("FrontendGameTokenRefreshed")


def _should_refresh_for_path(path: str) -> bool:
    return path.startswith(GAME_TOKEN_REFRESH_PATH_PREFIXES)


def _is_session_replaced_response(response: Response) -> bool:
    """Detect the backend single-session 409 reply by the HX-Trigger header."""
    if response.status_code != 409:
        return False
    trigger = response.headers.get("HX-Trigger") or response.headers.get("hx-trigger")
    if not trigger:
        return False
    return "session-replaced" in trigger


def _token_needs_refresh(token: str) -> bool:
    exp = _token_exp(token)
    if exp is None:
        return True
    now = int(datetime.now(UTC).timestamp())
    return exp <= now + GAME_TOKEN_REFRESH_GRACE_SECONDS


def _token_exp(token: str) -> int | None:
    try:
        _header, payload_raw, _signature = token.split(".")
        payload = json.loads(_b64url_decode(payload_raw))
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        return None
    exp = payload.get("exp") if isinstance(payload, dict) else None
    return exp if isinstance(exp, int) else None


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
