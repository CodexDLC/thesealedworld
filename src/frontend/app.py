"""
Frontend application entry point.

Structure:
- site_features: Web portal features (auth, cabinet, static pages)
- game_features: Core game logic (lobby, menu, scenario interaction)
"""

import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, cast

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.requests import Request

from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.config.settings import settings
from src.frontend.core.middleware import AuthUserMiddleware, SiteAnalyticsMiddleware
from src.frontend.core.renderer import get_ui_renderer
from src.frontend.core.routing import include_frontend_routers
from src.frontend.game_features.game_menu import GameMenuMiddleware
from src.shared.logging_config import setup_logging

setup_logging(
    settings=settings,
    service_name="frontend",
    intercept_loggers=["uvicorn", "fastapi"],
    log_levels={"httpx": 30},
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Frontend startup started")
    if settings.debug:
        logger.info("Frontend running in DEBUG mode")

    # Store templates in state for the UIRenderer dependency
    try:
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
        app.state.templates.env.filters["combat_log_time"] = combat_log_time_filter

        app.state.backend_http_client = httpx.AsyncClient(timeout=10.0)
        app.state.site_analytics = {}
    except Exception:
        logger.opt(exception=True).critical("Frontend startup failed")
        raise
    logger.info(
        "Frontend startup finished: templates_dir={} static_dir={}", settings.templates_dir, settings.static_dir
    )

    yield

    # Shutdown logic
    try:
        await app.state.backend_http_client.aclose()
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

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

app.add_middleware(AuthUserMiddleware)
app.add_middleware(SiteAnalyticsMiddleware)
app.add_middleware(GameMenuMiddleware)
include_frontend_routers(app)
include_cabinet(app, modules=CABINET_MODULES, mount_path="/cabinet")


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
