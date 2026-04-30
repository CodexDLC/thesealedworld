from collections.abc import Sequence

from fastapi import APIRouter, FastAPI

from src.frontend.game_features.game_lobby.routes.pages import router as game_lobby_router
from src.frontend.game_features.scenario.routes.pages import router as scenario_router

# Architecture Note:
# Features are split into two main categories:
# 1. site_features: Web-portal logic (Authentication, User Cabinet, Landing/Static pages)
# 2. game_features: Core gameplay interactions (Lobby, Menu systems, Game Scenarios)
from src.frontend.site_features.auth.routes.pages import router as auth_router
from src.frontend.site_features.cabinet.routes.pages import router as cabinet_router
from src.frontend.site_features.site.routes import router as frontend_pages_router

FRONTEND_ROUTERS: Sequence[APIRouter] = (
    frontend_pages_router,
    auth_router,
    cabinet_router,
    game_lobby_router,
    scenario_router,
)


def include_frontend_routers(app: FastAPI) -> None:
    for router in FRONTEND_ROUTERS:
        app.include_router(router)
