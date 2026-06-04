"""Studio FastAPI entry point.

Local-only. Never deployed to prod. Reuses `src/frontend/templates` and
`src/frontend/static` as a shared design-system base. Serves an analytical
cabinet that, in this PR, contains only the shell + a hello-world page —
analytical modules are added one PR at a time per the migration plan.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader
from loguru import logger

from fastapi_cabinet import include_cabinet
from src.shared.infrastructure.logging_config import setup_logging
from src.studio.cabinet import CABINET_MODULES
from src.studio.features.shell.routes import router as shell_router
from src.studio.features.source_selector.middleware import SourceSelectorMiddleware
from src.studio.features.source_selector.routes import router as source_selector_router
from src.studio.features.sources.postgres_readonly import PostgresPoolRegistry
from src.studio.features.sources.redis_readonly import RedisClientRegistry
from src.studio.features.sources.ssh_tunnel import SshTunnelManager
from src.studio.settings import settings

setup_logging(
    settings=settings,
    service_name="studio",
    intercept_loggers=["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"],
    log_levels={
        "asyncpg": 30,
        "boto3": 30,
        "botocore": 30,
        "httpx": 30,
        "urllib3": 30,
        "uvicorn.access": 30,
    },
)


def _inline_css_factory():
    """Return an `inline_css(path)` template global that reads from frontend/static.

    Studio reuses the prod frontend's CSS bundle, so the path is resolved
    against `frontend_static_dir`. Errors are swallowed and return an empty
    string (the link tag in the template is the production fallback).
    """
    _cache: dict[str, str] = {}

    def inline_css(file_path: str) -> str:
        if not settings.debug and file_path in _cache:
            return _cache[file_path]
        full_path = settings.frontend_static_dir / file_path
        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            logger.bind(path=str(full_path)).opt(exception=True).warning("StudioInlineCssFailed")
            return ""
        if not settings.debug:
            _cache[file_path] = content
        return content

    return inline_css


def _build_templates() -> Jinja2Templates:
    """Build Jinja2Templates with studio templates first, frontend templates as fallback."""
    loader = ChoiceLoader(
        [
            FileSystemLoader(str(settings.studio_templates_dir)),
            FileSystemLoader(str(settings.frontend_templates_dir)),
        ]
    )
    templates = Jinja2Templates(directory=str(settings.studio_templates_dir))
    templates.env.loader = loader
    templates.env.globals["inline_css"] = _inline_css_factory()
    templates.env.globals["static_version"] = "studio"
    return templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("StudioStartupStarted")

    app.state.templates = _build_templates()
    app.state.ssh_tunnel = SshTunnelManager(mode="detect")
    app.state.pg_pools = PostgresPoolRegistry()
    app.state.redis_clients = RedisClientRegistry()
    # Long-lived httpx client used by cabinet modules to call the backend API
    # at request.state.source.api_base (set per-request by SourceSelectorMiddleware).
    app.state.backend_http_client = httpx.AsyncClient(timeout=10.0)

    logger.bind(
        templates_studio=str(settings.studio_templates_dir),
        templates_frontend=str(settings.frontend_templates_dir),
        static_frontend=str(settings.frontend_static_dir),
        port=settings.app_port,
    ).info("StudioStartupFinished")

    try:
        yield
    finally:
        try:
            await app.state.backend_http_client.aclose()
            await app.state.pg_pools.close_all()
            await app.state.redis_clients.close_all()
            await app.state.ssh_tunnel.shutdown()
        except Exception:  # noqa: BLE001
            logger.opt(exception=True).warning("StudioShutdownErrors")
        logger.info("StudioShutdownFinished")


app = FastAPI(
    title="TurnBasedMMORPG Studio",
    debug=settings.debug,
    lifespan=lifespan,
)

# Mount the frontend's static dir at /static so base_cabinet.html (fonts, CSS,
# Alpine, etc.) resolves identically to prod.
app.mount("/static", StaticFiles(directory=str(settings.frontend_static_dir)), name="static")
# Studio-specific static overrides at /studio-static (used only when we need
# something the shared bundle doesn't cover).
if settings.studio_static_dir.exists():
    app.mount(
        "/studio-static",
        StaticFiles(directory=str(settings.studio_static_dir)),
        name="studio-static",
    )

app.add_middleware(SourceSelectorMiddleware, settings=settings)

app.include_router(shell_router)
app.include_router(source_selector_router)

include_cabinet(
    app,
    modules=CABINET_MODULES,
    mount_path="/admin",
    static_mount_path="/cabinet-assets",
)
