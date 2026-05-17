from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.exceptions import BaseAPIException, api_exception_handler
from src.backend.core.lifespan import lifespan
from src.backend.core.middleware import ActiveCharacterDirtySyncMiddleware
from src.shared.logging_config import setup_logging

setup_logging(
    settings=settings,
    service_name="backend",
    intercept_loggers=["uvicorn", "sqlalchemy.engine", "fastapi"],
    log_levels={"httpx": 30, "sqlalchemy.engine": 30},
)

from src.backend.features.arena.api import router as arena_router  # noqa: E402
from src.backend.features.character.api import router as character_router  # noqa: E402
from src.backend.features.combat.api import router as combat_router  # noqa: E402
from src.backend.features.exploration.api import router as exploration_router  # noqa: E402
from src.backend.features.game_catalog.api import router as game_catalog_router  # noqa: E402
from src.backend.features.game_lobby.api import router as game_lobby_router  # noqa: E402
from src.backend.features.game_session.api import router as game_session_router  # noqa: E402
from src.backend.features.inventory.api import router as inventory_router  # noqa: E402
from src.backend.features.scenario.api import router as scenario_router  # noqa: E402
from src.backend.features.tavern.api import router as tavern_router  # noqa: E402
from src.backend.features_site.combat.router import router as combat_internal_router  # noqa: E402
from src.backend.features_site.exploration.router import router as exploration_internal_router  # noqa: E402
from src.backend.features_site.game_config.router import router as game_config_router  # noqa: E402
from src.backend.features_site.scenario.router import router as scenario_internal_router  # noqa: E402

app = FastAPI(
    title="TurnBasedMMORPG Backend",
    lifespan=lifespan,
)

app.add_middleware(ActiveCharacterDirtySyncMiddleware)
app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore[arg-type]
app.include_router(game_config_router)
app.include_router(combat_internal_router)
app.include_router(scenario_internal_router)
app.include_router(exploration_internal_router)
app.include_router(arena_router)
app.include_router(character_router)
app.include_router(combat_router)
app.include_router(game_catalog_router)
app.include_router(inventory_router)
app.include_router(game_lobby_router)
app.include_router(game_session_router)
app.include_router(scenario_router)
app.include_router(exploration_router)
app.include_router(tavern_router)
logger.info(
    "Backend routers registered: arena, character, combat, game_catalog, inventory, game_lobby, game_session, scenario, exploration, tavern"
)


@app.get("/")
async def root():
    return {"status": "online", "service": "backend-logic", "features": ["event-bus", "game-streams"]}


@app.get("/health")
async def health():
    return {"status": "ok"}
