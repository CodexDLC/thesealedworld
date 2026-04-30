"""
Frontend application entry point.

Structure:
- site_features: Web portal features (auth, cabinet, static pages)
- game_features: Core game logic (lobby, menu, scenario interaction)
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from src.frontend.config.settings import settings
from src.frontend.core.middleware import AuthUserMiddleware
from src.frontend.core.renderer import get_ui_renderer
from src.frontend.core.routing import include_frontend_routers
from src.frontend.game_features.game_menu import GameMenuMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    if settings.debug:
        print("🛠️  Frontend running in DEBUG mode")

    # Store templates in state for the UIRenderer dependency
    app.state.templates = Jinja2Templates(directory=str(settings.templates_dir))
    app.state.backend_http_client = httpx.AsyncClient(timeout=10.0)

    yield

    # Shutdown logic
    await app.state.backend_http_client.aclose()
    print("👋 Shutting down frontend server")


# Initialize FastAPI app
app = FastAPI(
    title="TurnBasedMMORPG Frontend",
    debug=settings.debug,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

app.add_middleware(AuthUserMiddleware)
app.add_middleware(GameMenuMiddleware)
include_frontend_routers(app)


@app.get("/health")
async def health():
    """Health check endpoint for Docker/orchestrator."""
    return {"status": "ok", "service": "frontend"}


# ── ERROR HANDLERS ──


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    ui = get_ui_renderer(request)
    return await ui.render("errors/404.html", context={"error": "PAGE_NOT_FOUND"}, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    ui = get_ui_renderer(request)
    return await ui.render("errors/500.html", context={"error": str(exc)}, status_code=500)
