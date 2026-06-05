from collections.abc import Sequence

from fastapi import APIRouter, FastAPI
from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.core.routing_play import PLAY_ROUTERS
from src.frontend.core.routing_site import SITE_ROUTERS

FrontendSurface = str

FRONTEND_ROUTERS: Sequence[APIRouter] = (*SITE_ROUTERS, *PLAY_ROUTERS)


def routers_for_surface(surface: FrontendSurface) -> Sequence[APIRouter]:
    if surface == "site":
        return SITE_ROUTERS
    if surface == "play":
        return PLAY_ROUTERS
    if surface == "all":
        return FRONTEND_ROUTERS
    raise ValueError(f"Unsupported frontend surface: {surface!r}")


def include_frontend_routers(app: FastAPI, *, surface: FrontendSurface | None = None) -> None:
    active_surface = surface or settings.frontend_surface
    for router in routers_for_surface(active_surface):
        app.include_router(router)
        logger.bind(surface=active_surface, tags=router.tags).debug("FrontendRouterRegistered")
