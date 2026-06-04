"""Studio shell routes — home page that confirms the wiring is alive."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse

if TYPE_CHECKING:
    from src.studio.features.sources.ssh_tunnel import SshTunnelManager

router = APIRouter(tags=["studio-shell"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the studio landing page using the active source."""
    source = request.state.source
    tunnel_manager: SshTunnelManager = request.app.state.ssh_tunnel
    tunnel_check = await tunnel_manager.ensure(source)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "studio/home.html",
        {
            "request": request,
            "studio_source_kind": source.kind,
            "studio_source_label": source.label,
            "studio_source_badge_color": source.badge_color,
            "tunnel_check": tunnel_check,
            # Stand-in so base_cabinet.html doesn't NameError on optional `user`.
            "user": None,
        },
    )


@router.get("/health")
async def health() -> dict[str, str]:
    """Health endpoint for the local dev launcher."""
    return {"status": "ok", "service": "studio"}
