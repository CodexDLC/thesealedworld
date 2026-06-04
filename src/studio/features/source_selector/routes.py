"""Routes for switching the active data source.

`POST /studio/source` — sets the `studio_source` cookie and redirects back
to the page the user came from (HX-Redirect for HTMX). Called by the Source
Switcher dropdown in the studio header.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from starlette.responses import RedirectResponse, Response

from src.studio.features.source_selector.middleware import SOURCE_COOKIE_NAME

router = APIRouter(prefix="/studio", tags=["studio-shell"])

_VALID_KINDS = ("local", "prod")
_COOKIE_MAX_AGE_DAYS = 365


@router.post("/source")
async def set_source(
    request: Request,
    source: str = Form(...),
    next_url: str = Form("/"),
) -> Response:
    """Set the active data source and bounce back to where the user was.

    Invalid sources are silently rejected — the cookie is left as-is.
    """
    response: Response
    if source in _VALID_KINDS:
        response = RedirectResponse(url=next_url, status_code=303)
        response.set_cookie(
            key=SOURCE_COOKIE_NAME,
            value=source,
            max_age=_COOKIE_MAX_AGE_DAYS * 24 * 3600,
            httponly=False,  # readable from JS for badge updates without reload
            samesite="lax",
        )
        if "HX-Request" in request.headers:
            response.headers["HX-Redirect"] = next_url
        return response

    response = RedirectResponse(url=next_url, status_code=303)
    if "HX-Request" in request.headers:
        response.headers["HX-Redirect"] = next_url
    return response
