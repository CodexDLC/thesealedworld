from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.features.auth.token_state import get_access_token
from src.frontend.game_features.session.token_state import get_game_access_token


class UIRenderer:
    """
    Advanced UI Renderer for the Gateway.
    Handles global context injection and HTMX-specific logic.
    """

    def __init__(self, request: Request, templates: Jinja2Templates):
        self.request = request
        self.templates = templates

    async def render(self, template_name: str, context: dict[str, Any] | None = None, status_code: int = 200):
        """
        Render template with automatic global context.
        """
        context = context or {}

        # 1. Automatic Global Context
        # We pull data from request.state where middleware/dependencies put it
        global_context = {
            "request": self.request,
            "user": getattr(self.request.state, "user", None),
            "access_token": get_game_access_token(self.request) or get_access_token(self.request) or "",
            "site_access_token": get_access_token(self.request) or "",
            "game_access_token": get_game_access_token(self.request) or "",
            "static_version": _static_version(),
            "is_htmx": "HX-Request" in self.request.headers,
            "google_analytics_id": settings.google_analytics_id,
            "google_site_verification": settings.google_site_verification,
        }

        # 2. Dynamic Game Menu (if domain is provided in context)
        if context and "domain" in context and "nav" not in context:
            menu_service = getattr(self.request.state, "game_menu_service", None)
            if menu_service:
                global_context["nav"] = menu_service.build_menu(context["domain"])
            else:
                logger.warning("Menu service missing while rendering domain page: template={}", template_name)

        # 2. Merge contexts
        final_context = {**global_context, **context}

        # 3. Handle HTMX Fragments (optional logic)
        # If we want to automatically switch base templates based on HX-Request,
        # we can pass 'base_template' to the context.
        # If we want to automatically switch base templates based on HX-Request,
        # we can pass 'base_template' to the context.
        if global_context["is_htmx"] and "base_template" not in final_context:
            final_context["base_template"] = "shared/minimal.html"
        elif "base_template" not in final_context:
            final_context["base_template"] = "site/base_site.html"

        logger.info(
            "Template rendered: template={} status={} htmx={}",
            template_name,
            status_code,
            global_context["is_htmx"],
        )
        return self.templates.TemplateResponse(
            request=self.request,
            name=template_name,
            context=final_context,
            status_code=status_code,
        )


def get_ui_renderer(request: Request) -> UIRenderer:
    """
    Dependency to get an initialized UIRenderer.
    Requires 'templates' to be attached to app.state.
    """
    return UIRenderer(request, request.app.state.templates)


def _static_version() -> str:
    asset_paths = (
        settings.static_dir / "css" / "site.css",
        settings.static_dir / "js" / "site.js",
        settings.static_dir / "css" / "game.css",
        settings.static_dir / "js" / "game.js",
        settings.static_dir / "css" / "account.css",
        settings.static_dir / "css" / "cabinet.css",
    )
    mtimes = [_mtime(path) for path in asset_paths]
    return str(max(mtimes))


def _mtime(path: Path) -> int:
    try:
        return int(path.stat().st_mtime)
    except OSError:
        return 0
