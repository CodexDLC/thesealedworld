from collections.abc import Sequence

from fastapi import APIRouter

from src.frontend.game_features.arena.routes.actions import router as arena_router
from src.frontend.game_features.character_status.routes.fragments import router as character_status_router
from src.frontend.game_features.city_services.routes.actions import router as city_services_router
from src.frontend.game_features.combat.routes.actions import router as combat_router
from src.frontend.game_features.exploration.routes.actions import router as exploration_router
from src.frontend.game_features.game_catalog.routes.bootstrap import router as game_catalog_router
from src.frontend.game_features.game_lobby.routes.pages import router as game_lobby_router
from src.frontend.game_features.inventory.routes.fragments import router as inventory_router
from src.frontend.game_features.rift.routes.pages import router as rift_router
from src.frontend.game_features.scenario.routes.pages import router as scenario_router
from src.frontend.game_features.session.routes.pages import router as game_session_router

PLAY_ROUTERS: Sequence[APIRouter] = (
    arena_router,
    character_status_router,
    city_services_router,
    combat_router,
    exploration_router,
    game_catalog_router,
    game_lobby_router,
    inventory_router,
    rift_router,
    scenario_router,
    game_session_router,
)
