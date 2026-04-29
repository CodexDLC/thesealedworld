from collections.abc import Sequence

from fastapi import APIRouter, FastAPI

from src.frontend.features.auth.routes.pages import router as auth_router
from src.frontend.features.cabinet.routes.pages import router as cabinet_router
from src.frontend.features.game_lobby.routes.pages import router as game_lobby_router
from src.frontend.features.routes import router as frontend_pages_router

FRONTEND_ROUTERS: Sequence[APIRouter] = (
    frontend_pages_router,
    auth_router,
    cabinet_router,
    game_lobby_router,
)


def include_frontend_routers(app: FastAPI) -> None:
    for router in FRONTEND_ROUTERS:
        app.include_router(router)
