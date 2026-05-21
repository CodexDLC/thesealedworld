from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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
            "google_tag_manager_id": settings.google_tag_manager_id,
            "google_analytics_id": settings.google_analytics_id,
            "google_site_verification": settings.google_site_verification,
        }

        # 2. Dynamic Game Menu (if domain is provided in context)
        if context and "domain" in context and "nav" not in context:
            menu_service = getattr(self.request.state, "game_menu_service", None)
            if menu_service:
                global_context["nav"] = menu_service.build_menu(context["domain"])
            else:
                logger.bind(template=template_name).warning("MenuServiceMissing")

        # 2. Merge contexts
        final_context = {**global_context, **context}
        final_context["meta"] = _meta_context(self.request, final_context)

        # 3. Handle HTMX Fragments (optional logic)
        # If we want to automatically switch base templates based on HX-Request,
        # we can pass 'base_template' to the context.
        # If we want to automatically switch base templates based on HX-Request,
        # we can pass 'base_template' to the context.
        if global_context["is_htmx"] and "base_template" not in final_context:
            final_context["base_template"] = "shared/minimal.html"
        elif "base_template" not in final_context:
            final_context["base_template"] = "site/base_site.html"

        logger.bind(template=template_name, status_code=status_code, htmx=global_context["is_htmx"]).debug(
            "TemplateRendered"
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
        settings.static_dir / "css" / "fonts.css",
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


def _meta_context(request: Request, context: dict[str, Any]) -> dict[str, str]:
    provided = context.get("meta") or {}
    if not isinstance(provided, dict):
        provided = {}

    path = _request_path(request)
    canonical_url = _canonical_url(request, path)
    default_meta = {
        "site_name": settings.site_name,
        "title": settings.site_meta_title,
        "description": settings.site_meta_description,
        "image": settings.site_meta_image,
        "type": "website",
        "url": canonical_url,
        "robots": _robots_for_path(path),
        "locale": "ru_RU",
    }
    meta = {**default_meta, **provided}
    base_url = _site_base_url(request)
    meta["url"] = _absolute_url(str(meta.get("url") or canonical_url), base_url)
    meta["image"] = _absolute_url(str(meta.get("image") or settings.site_meta_image), base_url)
    return meta


def _site_base_url(request: Request) -> str:
    configured = settings.site_base_url.strip()
    if configured:
        return configured.rstrip("/")

    domain_name = str(getattr(settings, "domain_name", "") or "").strip()
    if domain_name:
        if domain_name.startswith(("http://", "https://")):
            return domain_name.rstrip("/")
        scheme = "http" if domain_name.startswith(("localhost", "127.0.0.1")) else "https"
        return f"{scheme}://{domain_name}".rstrip("/")

    return str(getattr(request, "base_url", "http://testserver/")).rstrip("/")


def _request_path(request: Request) -> str:
    url = getattr(request, "url", None)
    return str(getattr(url, "path", "/") or "/")


def _canonical_url(request: Request, path: str) -> str:
    url = getattr(request, "url", None)
    if url is not None:
        try:
            return str(url.replace(query=None, fragment=None))
        except (AttributeError, TypeError, ValueError):
            pass
    return f"{_site_base_url(request)}{path}"


def _absolute_url(value: str, base_url: str) -> str:
    if not value:
        return ""
    if urlsplit(value).scheme:
        return value
    if not value.startswith("/"):
        value = f"/{value}"
    return f"{base_url}{value}"


def _robots_for_path(path: str) -> str:
    noindex_prefixes = (
        "/login",
        "/register",
        "/logout",
        "/account",
        "/admin",
        "/game-lobby",
        "/game",
        "/api",
        "/system",
        "/survey",
    )
    if path.startswith(noindex_prefixes):
        return "noindex, nofollow"
    return "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"
