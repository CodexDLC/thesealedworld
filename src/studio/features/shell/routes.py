"""Studio shell routes — landing page lists the registered cabinet modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from starlette.responses import HTMLResponse

from fastapi_cabinet import cabinet_site

if TYPE_CHECKING:
    from src.studio.features.sources.ssh_tunnel import SshTunnelManager

router = APIRouter(tags=["studio-shell"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the studio landing page with module tiles."""
    source = request.state.source
    tunnel_manager: SshTunnelManager = request.app.state.ssh_tunnel
    tunnel_check = await tunnel_manager.ensure(source)

    # Pull the registered modules from the global cabinet site and group them
    # by their declared group_label so the tiles read like the cabinet sidebar.
    modules = sorted(cabinet_site.registry.all(), key=lambda m: (m.order, m.key))
    groups: dict[str, list] = {}
    for module in modules:
        groups.setdefault(module.group_label or "Другое", []).append(module)

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
            "groups": groups,
            # Stand-in so base_cabinet.html doesn't NameError on optional `user`.
            "user": None,
        },
    )


@router.get("/health")
async def health() -> dict[str, str]:
    """Health endpoint for the local dev launcher."""
    return {"status": "ok", "service": "studio"}
