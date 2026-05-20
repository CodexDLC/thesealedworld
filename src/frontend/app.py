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
from src.frontend.core.database.session import close_db_engine, create_db_tables
from src.frontend.core.middleware import AuthUserMiddleware, SiteAnalyticsMiddleware
from src.frontend.core.renderer import get_ui_renderer
from src.frontend.core.routing import include_frontend_routers
from src.frontend.features.account.middleware.account_auth import AccountAuthMiddleware
from src.frontend.features.auth.token_state import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from src.frontend.features.cabinet.middleware.admin_auth import AdminAuthMiddleware
from src.frontend.features.player_analytics.tasks.rollup_task import player_presence_rollup_loop
from src.frontend.game_features.game_menu import GameMenuMiddleware
from src.frontend.game_features.session.cookies import clear_active_character_cookie
from src.frontend.game_features.session.middleware import GameTokenRefreshMiddleware
from src.frontend.game_features.session.token_state import clear_game_token_cookies
from src.shared.exceptions import BaseAPIException
from src.shared.logging_config import setup_logging

setup_logging(
    settings=settings,
    service_name="frontend",
    intercept_loggers=["uvicorn", "fastapi"],
    log_levels={"httpx": 30},
)


def split_bracket_coords_label(text: str | None) -> dict[str, str | None]:
    if not text:
        return {"label": "", "coords": None}
    value = str(text).strip()
    match = re.match(r"^(?P<label>.*?)\s*\[(?P<coords>-?\d+\s*:\s*-?\d+)\]\s*$", value)
    if not match:
        return {"label": value, "coords": None}
    return {"label": match.group("label").strip(), "coords": match.group("coords").replace(" ", "")}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Frontend startup started")
    if settings.debug:
        logger.info("Frontend running in DEBUG mode")

    # Store templates in state for the UIRenderer dependency
    try:
        await create_db_tables()

        app.state.templates = Jinja2Templates(directory=str(settings.templates_dir))

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
        logger.opt(exception=True).critical("Frontend startup failed")
        raise
    logger.info(
        "Frontend startup finished: templates_dir={} static_dir={}", settings.templates_dir, settings.static_dir
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
        logger.opt(exception=True).critical("Frontend shutdown failed")
        raise
    logger.info("Frontend shutdown finished")


# Initialize FastAPI app
app = FastAPI(
    title="TurnBasedMMORPG Frontend",
    debug=settings.debug,
    lifespan=lifespan,
)

# Mount generated assets before the broad /static mount so runtime files are not looked up in src/frontend/static.
settings.generated_assets_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/static/generated-assets",
    StaticFiles(directory=str(settings.generated_assets_dir)),
    name="generated_assets",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

app.add_middleware(AccountAuthMiddleware)
app.add_middleware(AdminAuthMiddleware)
app.add_middleware(AuthUserMiddleware)
app.add_middleware(SiteAnalyticsMiddleware)
app.add_middleware(GameMenuMiddleware)
app.add_middleware(GameTokenRefreshMiddleware)
include_frontend_routers(app)
include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")


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
    logger.warning("Frontend 404: method={} path={}", request.method, request.url.path)
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
    logger.warning(
        "Frontend backend request failed: method={} path={} backend_status={} backend_url={}",
        request.method,
        request.url.path,
        backend_status,
        exc.request.url,
    )
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
    logger.warning(
        "Frontend backend unavailable: method={} path={} error={}",
        request.method,
        request.url.path,
        exc,
    )
    ui = get_ui_renderer(request)
    return await ui.render(
        "errors/500.html",
        context={"error": "GAME_BACKEND_UNAVAILABLE"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    logger.opt(exception=exc).critical(
        "Frontend 500: method={} path={} error={}",
        request.method,
        request.url.path,
        exc.__class__.__name__,
    )
    ui = get_ui_renderer(request)
    return await ui.render("errors/500.html", context={"error": str(exc)}, status_code=500)


def _auth_recovery_location(request: Request) -> str:
    path = request.url.path
    if path.startswith(
        ("/game", "/api/game", "/scenario", "/combat", "/exploration", "/inventory", "/arena", "/city-services")
    ):
        return "/game-lobby"
    return "/login"


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
        response.delete_cookie(ACCESS_COOKIE_NAME)
        response.delete_cookie(REFRESH_COOKIE_NAME)
    if "HX-Request" in request.headers:
        response.headers["HX-Redirect"] = location
    return response
