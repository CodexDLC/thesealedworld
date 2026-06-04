"""Attach the active `Source` to every request.

Resolution order:
1. Cookie `studio_source` (set by the Source Switcher dropdown).
2. Fallback: `settings.studio_source` (env / default `local`).

Invalid cookie values are ignored and treated as missing — the user can
recover by selecting a valid option from the dropdown.

The chosen `Source` is exposed at `request.state.source`. Templates also see
it via the `studio_source` context variable (injected by the home route /
cabinet providers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

if TYPE_CHECKING:
    from src.studio.features.sources.models import Source, SourceKind
    from src.studio.settings import StudioSettings

SOURCE_COOKIE_NAME = "studio_source"
_VALID_KINDS: frozenset[str] = frozenset(("local", "prod"))


class SourceSelectorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, settings: StudioSettings) -> None:
        super().__init__(app)
        self._settings = settings
        self._sources = settings.sources()

    async def dispatch(self, request: Request, call_next) -> Response:
        kind = self._resolve_kind(request)
        source: Source = self._sources[kind]
        request.state.source = source
        request.state.source_kind = kind
        return await call_next(request)

    def _resolve_kind(self, request: Request) -> SourceKind:
        cookie_value = request.cookies.get(SOURCE_COOKIE_NAME)
        if cookie_value in _VALID_KINDS:
            return cookie_value  # type: ignore[return-value]
        return self._settings.studio_source
