from collections.abc import Sequence

from fastapi import APIRouter, FastAPI
from loguru import logger

from src.frontend.game_features.arena.routes.actions import router as arena_router
from src.frontend.game_features.character_status.routes.fragments import router as character_status_router
from src.frontend.game_features.combat.routes.actions import router as combat_router
from src.frontend.game_features.exploration.routes.actions import router as exploration_router
from src.frontend.game_features.game_catalog.routes.bootstrap import router as game_catalog_router
from src.frontend.game_features.game_lobby.routes.pages import router as game_lobby_router
from src.frontend.game_features.scenario.routes.pages import router as scenario_router
from src.frontend.game_features.session.routes.pages import router as game_session_router

# Architecture Note:
# Features are split into two main categories:
# 1. site_features: Web-portal logic (Authentication, User Cabinet, Landing/Static pages)
# 2. game_features: Core gameplay interactions (Lobby, Menu systems, Game Scenarios)
from src.frontend.site_features.auth.routes.pages import router as auth_router
from src.frontend.site_features.site.routes import router as frontend_pages_router

FRONTEND_ROUTERS: Sequence[APIRouter] = (
    frontend_pages_router,
    auth_router,
    arena_router,
    character_status_router,
    combat_router,
    exploration_router,
    game_catalog_router,
    game_lobby_router,
    scenario_router,
    game_session_router,
)


def include_frontend_routers(app: FastAPI) -> None:
    for router in FRONTEND_ROUTERS:
        app.include_router(router)
        logger.info("Frontend router registered: tags={}", router.tags)
