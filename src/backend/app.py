from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.exceptions import BaseAPIException, api_exception_handler
from src.backend.core.lifespan import lifespan
from src.backend.core.middleware import ActiveCharacterDirtySyncMiddleware
from src.shared.infrastructure.log_middleware import LogContextMiddleware
from src.shared.infrastructure.logging_config import setup_logging
from src.shared.infrastructure.metrics_endpoint import metrics_router
from src.shared.infrastructure.metrics_middleware import PrometheusMiddleware

setup_logging(
    settings=settings,
    service_name="backend",
    intercept_loggers=["uvicorn", "sqlalchemy.engine", "fastapi"],
    log_levels={"httpx": 30, "sqlalchemy.engine": 30},
)

from src.backend.features.arena.api import router as arena_router  # noqa: E402
from src.backend.features.character.api import router as character_router  # noqa: E402
from src.backend.features.city_services.api import router as city_services_router  # noqa: E402
from src.backend.features.combat.api import router as combat_router  # noqa: E402
from src.backend.features.combat.api.analytics_router import router as combat_analytics_router  # noqa: E402
from src.backend.features.combat.api.internal_router import router as combat_internal_router  # noqa: E402
from src.backend.features.exploration.api import router as exploration_router  # noqa: E402
from src.backend.features.exploration.api.internal_router import router as exploration_internal_router  # noqa: E402
from src.backend.features.game_catalog.api import router as game_catalog_router  # noqa: E402
from src.backend.features.game_config.api import router as game_config_router  # noqa: E402
from src.backend.features.game_lobby.api import router as game_lobby_router  # noqa: E402
from src.backend.features.game_session.api import router as game_session_router  # noqa: E402
from src.backend.features.inventory.api import router as inventory_router  # noqa: E402
from src.backend.features.monsters.api import router as monsters_router  # noqa: E402
from src.backend.features.scenario.api import router as scenario_router  # noqa: E402
from src.backend.features.scenario.api.internal_router import router as scenario_internal_router  # noqa: E402

app = FastAPI(
    title="TurnBasedMMORPG Backend",
    lifespan=lifespan,
)

app.add_middleware(ActiveCharacterDirtySyncMiddleware)
app.add_middleware(PrometheusMiddleware, service_name="backend")
app.add_middleware(LogContextMiddleware)
app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore[arg-type]
app.include_router(metrics_router)
app.include_router(game_config_router)
app.include_router(combat_internal_router)
app.include_router(scenario_internal_router)
app.include_router(exploration_internal_router)
app.include_router(arena_router)
app.include_router(character_router)
app.include_router(city_services_router)
app.include_router(combat_analytics_router)
app.include_router(combat_router)
app.include_router(game_catalog_router)
app.include_router(inventory_router)
app.include_router(monsters_router)
app.include_router(game_lobby_router)
app.include_router(game_session_router)
app.include_router(scenario_router)
app.include_router(exploration_router)
logger.bind(
    routers=[
        "arena",
        "character",
        "city_services",
        "combat_analytics",
        "combat",
        "game_catalog",
        "inventory",
        "monsters",
        "game_lobby",
        "game_session",
        "scenario",
        "exploration",
    ],
).info("BackendRoutersRegistered")


@app.get("/")
async def root():
    return {"status": "online", "service": "backend-logic", "features": ["event-bus", "game-streams"]}


@app.get("/health")
async def health():
    return {"status": "ok"}
