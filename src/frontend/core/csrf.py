from __future__ import annotations

import hmac
import secrets
from collections.abc import Awaitable, Callable
from http import cookies as http_cookies
from typing import Any
from urllib.parse import parse_qs

from loguru import logger
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.frontend.config.settings import settings

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Endpoints that use Bearer auth or are otherwise outside the browser-form scope.
CSRF_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "/auth/",
    "/static/",
    "/metrics",
)
CSRF_SKIP_EXACT_PATHS: frozenset[str] = frozenset({"/health", "/favicon.ico"})

_FORM_CONTENT_TYPES = (
    "application/x-www-form-urlencoded",
    "multipart/form-data",
)

_TOKEN_BYTES = 32


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _should_skip(path: str) -> bool:
    return path in CSRF_SKIP_EXACT_PATHS or path.startswith(CSRF_SKIP_PATH_PREFIXES)


def _is_form_content_type(content_type: str) -> bool:
    lowered = content_type.lower()
    return any(lowered.startswith(ct) for ct in _FORM_CONTENT_TYPES)


def _parse_cookie(cookie_header: str, name: str) -> str | None:
    if not cookie_header:
        return None
    jar = http_cookies.SimpleCookie()
    try:
        jar.load(cookie_header)
    except http_cookies.CookieError:
        return None
    morsel = jar.get(name)
    return morsel.value if morsel is not None else None


def _build_set_cookie(name: str, value: str) -> str:
    parts = [
        f"{name}={value}",
        "Path=/",
        "Max-Age=604800",  # 7 days
        "SameSite=Lax",
    ]
    if settings.auth_cookie_secure:
        parts.append("Secure")
    return "; ".join(parts)


async def _buffer_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        more_body = message.get("more_body", False)
    return b"".join(chunks)


def _replayed_receive(body: bytes) -> Receive:
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


class CsrfMiddleware:
    """Double-submit CSRF for browser forms.

    Pure ASGI implementation: the request body must be re-emitted to downstream
    handlers after we read it to look up the token, which Starlette's
    BaseHTTPMiddleware does not support cleanly.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope["method"]
        path: str = scope["path"]
        headers: dict[str, str] = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        cookie_token = _parse_cookie(headers.get("cookie", ""), settings.csrf_cookie_name)

        scope.setdefault("state", {})
        state: dict[str, Any] = scope["state"]
        issued_token: str | None = None
        if cookie_token:
            state["csrf_token"] = cookie_token
        else:
            issued_token = generate_csrf_token()
            state["csrf_token"] = issued_token

        effective_receive = receive

        if method in UNSAFE_METHODS and not _should_skip(path):
            if not cookie_token:
                logger.bind(path=path).warning("CsrfRejectedNoCookie")
                await PlainTextResponse("CSRF token missing", status_code=403)(scope, receive, send)
                return

            presented = headers.get(settings.csrf_header_name.lower())
            if not presented and _is_form_content_type(headers.get("content-type", "")):
                body = await _buffer_body(receive)
                effective_receive = _replayed_receive(body)
                parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
                values = parsed.get(settings.csrf_field_name)
                presented = values[0] if values else None

            if not presented or not hmac.compare_digest(cookie_token, presented):
                logger.bind(path=path).warning("CsrfRejectedTokenMismatch")
                await PlainTextResponse("CSRF token invalid", status_code=403)(scope, effective_receive, send)
                return

        send_wrapped = self._wrap_send(send, issued_token) if issued_token else send
        await self.app(scope, effective_receive, send_wrapped)

    @staticmethod
    def _wrap_send(send: Send, issued_token: str) -> Callable[[Message], Awaitable[None]]:
        cookie_header = _build_set_cookie(settings.csrf_cookie_name, issued_token)

        async def wrapped(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append((b"set-cookie", cookie_header.encode("latin-1")))
                message["headers"] = headers_list
            await send(message)

        return wrapped
