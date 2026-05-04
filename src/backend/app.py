from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.exceptions import BaseAPIException, api_exception_handler
from src.backend.core.lifespan import lifespan
from src.shared.logging_config import setup_logging

setup_logging(
    settings=settings,
    service_name="backend",
    intercept_loggers=["uvicorn", "sqlalchemy.engine", "fastapi"],
    log_levels={"httpx": 30},
)

from src.backend.features.auth.api import router as auth_router  # noqa: E402
from src.backend.features.game_lobby.api import router as game_lobby_router  # noqa: E402
from src.backend.features.scenario.api import router as scenario_router  # noqa: E402

app = FastAPI(
    title="TurnBasedMMORPG Backend",
    lifespan=lifespan,
)

app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore[arg-type]
app.include_router(auth_router)
app.include_router(game_lobby_router)
app.include_router(scenario_router)
logger.info("Backend routers registered: auth, game_lobby, scenario")


@app.get("/")
async def root():
    return {"status": "online", "service": "backend-logic", "features": ["event-bus", "game-streams"]}


@app.get("/health")
async def health():
    return {"status": "ok"}
