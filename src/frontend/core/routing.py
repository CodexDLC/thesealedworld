from collections.abc import Sequence

from fastapi import APIRouter, FastAPI
from loguru import logger

# Architecture Note:
# Features are split into two main categories:
# 1. features: Site web logic (Authentication, User Cabinet, Library, Landing/Static pages)
# 2. game_features: Core gameplay interactions (Lobby, Menu systems, Game Scenarios)
from src.frontend.features.account.routes.pages import router as account_router
from src.frontend.features.auth.api import router as auth_api_router
from src.frontend.features.auth.routes.pages import router as auth_router
from src.frontend.features.feedback.routes.pages import router as feedback_router
from src.frontend.features.library.routes.pages import router as library_router
from src.frontend.features.public_site.routes.pages import router as frontend_pages_router
from src.frontend.features.surveys.routes.pages import router as surveys_router
from src.frontend.game_features.arena.routes.actions import router as arena_router
from src.frontend.game_features.character_status.routes.fragments import router as character_status_router
from src.frontend.game_features.city_services.routes.actions import router as city_services_router
from src.frontend.game_features.combat.routes.actions import router as combat_router
from src.frontend.game_features.exploration.routes.actions import router as exploration_router
from src.frontend.game_features.game_catalog.routes.bootstrap import router as game_catalog_router
from src.frontend.game_features.game_lobby.routes.pages import router as game_lobby_router
from src.frontend.game_features.inventory.routes.fragments import router as inventory_router
from src.frontend.game_features.scenario.routes.pages import router as scenario_router
from src.frontend.game_features.session.routes.pages import router as game_session_router

FRONTEND_ROUTERS: Sequence[APIRouter] = (
    frontend_pages_router,
    library_router,
    auth_api_router,
    auth_router,
    account_router,
    feedback_router,
    surveys_router,
    arena_router,
    character_status_router,
    city_services_router,
    combat_router,
    exploration_router,
    game_catalog_router,
    game_lobby_router,
    inventory_router,
    scenario_router,
    game_session_router,
)


def include_frontend_routers(app: FastAPI) -> None:
    for router in FRONTEND_ROUTERS:
        app.include_router(router)
        logger.info("Frontend router registered: tags={}", router.tags)
