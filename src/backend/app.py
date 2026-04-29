from fastapi import FastAPI

from src.backend.core.exceptions import BaseAPIException, api_exception_handler
from src.backend.core.lifespan import lifespan
from src.backend.features.auth.api import router as auth_router
from src.backend.features.game_lobby.api import router as game_lobby_router

app = FastAPI(
    title="TurnBasedMMORPG Backend",
    lifespan=lifespan,
)

app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore[arg-type]
app.include_router(auth_router)
app.include_router(game_lobby_router)


@app.get("/")
async def root():
    return {"status": "online", "service": "backend-logic", "features": ["event-bus", "game-streams"]}


@app.get("/health")
async def health():
    return {"status": "ok"}
