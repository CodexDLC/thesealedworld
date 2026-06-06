from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Baseline CSP. Permissive for inline scripts/styles because Alpine.js relies on
# inline expressions in templates; tighten with nonces in a later pass.
_BASELINE_IMG_SRC = ("'self'", "data:", "blob:")


def build_content_security_policy(*, image_origins: Iterable[str] = ()) -> str:
    img_src = [*_BASELINE_IMG_SRC]
    for origin in image_origins:
        normalized = _normalize_csp_origin(origin)
        if normalized and normalized not in img_src:
            img_src.append(normalized)

    return (
        "default-src 'self'; "
        f"img-src {' '.join(img_src)}; "
        "font-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'self'; "
        "base-uri 'self'"
    )


def _normalize_csp_origin(value: str) -> str:
    raw = value.strip().rstrip("/")
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return raw


_BASELINE_CSP = build_content_security_policy()

_DEFAULT_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": _BASELINE_CSP,
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers to every response."""

    def __init__(self, app, *, content_security_policy: str = _BASELINE_CSP) -> None:
        super().__init__(app)
        self._headers = {**_DEFAULT_HEADERS, "Content-Security-Policy": content_security_policy}

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in self._headers.items():
            response.headers.setdefault(name, value)
        return response
