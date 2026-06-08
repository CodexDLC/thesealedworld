"""
Frontend application entry point.

Structure:
- features: Site web features (auth, cabinet, static pages)
- game_features: Core game logic (lobby, menu, scenario interaction)
"""

import asyncio
import re
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Any, cast

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.requests import Request

from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.config.settings import settings
from src.frontend.core.csrf import CsrfMiddleware
from src.frontend.core.database.session import close_db_engine, create_db_tables
from src.frontend.core.middleware import AuthUserMiddleware, SiteAnalyticsMiddleware
from src.frontend.core.renderer import get_ui_renderer
from src.frontend.core.routing import include_frontend_routers
from src.frontend.core.security_headers import SecurityHeadersMiddleware, build_content_security_policy
from src.frontend.features.account.middleware.account_auth import AccountAuthMiddleware
from src.frontend.features.auth.token_state import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from src.frontend.features.cabinet.middleware.admin_auth import AdminAuthMiddleware
from src.frontend.features.player_analytics.tasks.rollup_task import player_presence_rollup_loop
from src.frontend.game_features.game_menu import GameMenuMiddleware
from src.frontend.game_features.session.cookies import clear_active_character_cookie
from src.frontend.game_features.session.middleware import GameTokenRefreshMiddleware
from src.frontend.game_features.session.token_state import clear_game_token_cookies
from src.frontend.integrations.generated_assets import configure_generated_asset_serving
from src.shared.exceptions import BaseAPIException
from src.shared.infrastructure.log_middleware import LogContextMiddleware
from src.shared.infrastructure.logging_config import setup_logging
from src.shared.infrastructure.metrics_endpoint import metrics_router
from src.shared.infrastructure.metrics_middleware import PrometheusMiddleware

SITE_SURFACES = {"all", "site"}
PLAY_SURFACES = {"all", "play"}

setup_logging(
    settings=settings,
    service_name="frontend",
    intercept_loggers=["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"],
    log_levels={
        "boto3": 30,
        "botocore": 30,
        "httpx": 30,
        "s3transfer": 30,
        "urllib3": 30,
        "uvicorn.access": 30,
    },
)


def split_bracket_coords_label(text: str | None) -> dict[str, str | None]:
    if not text:
        return {"label": "", "coords": None}
    value = str(text).strip()
    match = re.match(r"^(?P<label>.*?)\s*\[(?P<coords>-?\d+\s*:\s*-?\d+)\]\s*$", value)
    if not match:
        return {"label": value, "coords": None}
    return {"label": match.group("label").strip(), "coords": match.group("coords").replace(" ", "")}


# CSS inlining utility with in-memory caching for production environments
_css_cache: dict[str, str] = {}


def inline_css(file_path: str) -> str:
    """Read a CSS file from static directory and return its content. Caches in production."""
    if not settings.debug and file_path in _css_cache:
        return _css_cache[file_path]

    full_path = settings.static_dir / file_path
    try:
        content = full_path.read_text(encoding="utf-8")
        if not settings.debug:
            _css_cache[file_path] = content
        return content
    except Exception:
        logger.bind(path=str(full_path)).exception("FrontendCssInlineFailed")
        return ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.bind(surface=settings.frontend_surface).info("FrontendStartupStarted")
    if settings.debug:
        logger.info("FrontendDebugModeEnabled")

    # Store templates in state for the UIRenderer dependency
    try:
        await create_db_tables()

        app.state.templates = Jinja2Templates(directory=str(settings.templates_dir))
        # Render Python ``None`` as an empty string instead of the literal
        # "None". Без этого ``<img src="{{ vm.icon_url }}">`` (где icon_url is
        # None) производит ``<img src="None">`` → браузер делает GET на
        # ``/game/None`` → 404. Та же беда для href/data-*-url атрибутов.
        # Empty string keeps these tags inert (Chrome не fires request for
        # ``<img src="">``), но шаблоны с явной проверкой ``{% if x %}``
        # продолжают работать как и раньше.
        app.state.templates.env.finalize = lambda value: "" if value is None else value
        # Expose debug flag to templates so dev-only diagnostics (например,
        # подсветка отсутствующих SVG-иконок) можно рисовать только в dev.
        app.state.templates.env.globals["is_debug"] = settings.debug
        # Register global functions in templates
        app.state.templates.env.globals["inline_css"] = inline_css

        # Scenario rich text filter for automatic CAPS wrapping
        def scenario_rich_text_filter(text: str) -> str:
            if not text:
                return text
            # Matches uppercase blocks (8+ chars) not surrounded by lowercase letters
            pattern = r"(?<![а-яa-z])([А-ЯA-Z0-9\s\.,!\?\-\:\%\#\[\]]{8,})(?![а-яa-z])"

            def repl(m):
                seg = m.group(1).strip()
                if any(c.isupper() for c in seg) and len(seg) > 5:
                    return f'<span class="system-alert">{seg}</span>'
                return m.group(0)

            return re.sub(pattern, repl, text)

        def combat_log_time_filter(timestamp: int | float | str | None) -> str:
            if timestamp in (None, ""):
                return ""
            try:
                return datetime.fromtimestamp(float(cast("Any", timestamp))).strftime("%H:%M:%S")
            except (TypeError, ValueError, OSError):
                return ""

        app.state.templates.env.filters["scenario_rich_text"] = scenario_rich_text_filter
        app.state.templates.env.filters["split_bracket_coords"] = split_bracket_coords_label
        app.state.templates.env.filters["combat_log_time"] = combat_log_time_filter

        app.state.backend_http_client = httpx.AsyncClient(timeout=10.0)
        app.state.site_analytics = {}
        app.state.player_presence = {}
    except Exception:
        logger.opt(exception=True).critical("FrontendStartupFailed")
        raise
    logger.bind(templates_dir=str(settings.templates_dir), static_dir=str(settings.static_dir)).info(
        "FrontendStartupFinished"
    )

    rollup_task = asyncio.create_task(player_presence_rollup_loop(app))

    yield

    # Shutdown logic
    rollup_task.cancel()
    with suppress(asyncio.CancelledError):
        await rollup_task

    try:
        await app.state.backend_http_client.aclose()
        await close_db_engine()
    except Exception:
        logger.opt(exception=True).critical("FrontendShutdownFailed")
        raise
    logger.info("FrontendShutdownFinished")


# Initialize FastAPI app
app = FastAPI(
    title="TurnBasedMMORPG Frontend",
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure generated assets before the broad /static mount so runtime files are not looked up in src/frontend/static.
configure_generated_asset_serving(app, config=settings)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

if settings.frontend_surface in SITE_SURFACES:
    app.add_middleware(AccountAuthMiddleware)
    app.add_middleware(AdminAuthMiddleware)
app.add_middleware(AuthUserMiddleware)
app.add_middleware(SiteAnalyticsMiddleware)
if settings.frontend_surface in PLAY_SURFACES:
    app.add_middleware(GameMenuMiddleware)
    app.add_middleware(GameTokenRefreshMiddleware)
app.add_middleware(PrometheusMiddleware, service_name="frontend")
app.add_middleware(LogContextMiddleware)
generated_asset_image_origins = (
    [settings.asset_s3_endpoint_url]
    if settings.asset_storage_backend == "s3" and settings.asset_s3_endpoint_url
    else []
)
app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy=build_content_security_policy(image_origins=generated_asset_image_origins),
)
app.add_middleware(CsrfMiddleware)
include_frontend_routers(app, surface=settings.frontend_surface)
if settings.frontend_surface in SITE_SURFACES:
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin", static_mount_path="/cabinet-assets")
app.include_router(metrics_router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(settings.static_dir / "favicon.ico", media_type="image/x-icon")


@app.get("/health")
async def health():
    """Health check endpoint for Docker/orchestrator."""
    return {"status": "ok", "service": "frontend"}


# ── ERROR HANDLERS ──


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    logger.bind(method=request.method, path=request.url.path).warning(
        "FrontendNotFound method={} path={}",
        request.method,
        request.url.path,
    )
    ui = get_ui_renderer(request)
    return await ui.render("errors/404.html", context={"error": "PAGE_NOT_FOUND"}, status_code=404)


@app.exception_handler(BaseAPIException)
async def frontend_api_exception_handler(request: Request, exc: BaseAPIException):
    extra = dict(exc.extra)
    headers: dict[str, str] | None = extra.pop("headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error_code, "message": exc.detail, **extra}},
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def frontend_http_exception_handler(request: Request, exc: HTTPException):
    if status.HTTP_300_MULTIPLE_CHOICES <= exc.status_code < 400:
        location = (exc.headers or {}).get("Location") or "/"
        return _redirect_and_clear_expired_state(request, location, status_code=exc.status_code)

    if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
        return _redirect_and_clear_expired_state(request, _auth_recovery_location(request))

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.exception_handler(httpx.HTTPStatusError)
async def backend_http_status_handler(request: Request, exc: httpx.HTTPStatusError):
    backend_status = exc.response.status_code
    logger.bind(
        method=request.method,
        path=request.url.path,
        backend_status=backend_status,
        backend_url=str(exc.request.url),
    ).warning("FrontendBackendRequestFailed")
    if backend_status in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
        return _redirect_and_clear_expired_state(request, _auth_recovery_location(request))

    ui = get_ui_renderer(request)
    return await ui.render(
        "errors/500.html",
        context={"error": "GAME_BACKEND_REQUEST_FAILED"},
        status_code=status.HTTP_502_BAD_GATEWAY,
    )


@app.exception_handler(httpx.RequestError)
async def backend_request_error_handler(request: Request, exc: httpx.RequestError):
    logger.bind(method=request.method, path=request.url.path, error=str(exc)).warning("FrontendBackendUnavailable")
    ui = get_ui_renderer(request)
    return await ui.render(
        "errors/500.html",
        context={"error": "GAME_BACKEND_UNAVAILABLE"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    logger.bind(method=request.method, path=request.url.path, error_type=exc.__class__.__name__).opt(
        exception=exc
    ).critical("FrontendServerError")
    ui = get_ui_renderer(request)
    return await ui.render("errors/500.html", context={"error": str(exc)}, status_code=500)


def _auth_recovery_location(request: Request) -> str:
    path = request.url.path
    if path.startswith(
        ("/game", "/api/game", "/scenario", "/combat", "/exploration", "/inventory", "/arena", "/city-services")
    ):
        return "/game-lobby"
    return "/login?expired=1"


def _redirect_and_clear_expired_state(
    request: Request,
    location: str,
    *,
    status_code: int = status.HTTP_303_SEE_OTHER,
) -> RedirectResponse:
    response = RedirectResponse(location, status_code=status_code)
    clear_active_character_cookie(response)
    clear_game_token_cookies(response)
    if location.startswith("/login"):
        cookie_domain = settings.auth_cookie_domain or None
        for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
            response.delete_cookie(name, domain=cookie_domain)
            if cookie_domain:
                # Also expire any legacy host-only cookie left from before the
                # domain-scoped scheme, otherwise the stale duplicate keeps
                # resolving a dead session and the login loop persists.
                response.delete_cookie(name)
    if "HX-Request" in request.headers:
        response.headers["HX-Redirect"] = location
    return response
