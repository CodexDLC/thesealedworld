from typing import Annotated

from fastapi import APIRouter, Depends, Query
from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.features.library.services.library_service import LibraryFrontendService
from src.frontend.integrations.backend_api.game_catalog import BackendGameCatalogApi

router = APIRouter(tags=["Library"])


def get_library_service(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]) -> LibraryFrontendService:
    api = BackendGameCatalogApi(client=get_backend_http_client(ui.request), base_url=settings.backend_base_url)
    return LibraryFrontendService(catalog_api=api)


@router.get("/library", name="library")
async def library(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Library page."""
    return await ui.render("site/library.html")


@router.get("/library/fragments/intro", name="library_intro_fragment")
async def library_intro_fragment(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Library introduction fragment."""
    logger.bind(fragment="intro").debug("LibraryFragmentRequested")
    return await ui.render("site/library/fragments/intro.html")


@router.get("/library/fragments/monsters", name="library_monsters_fragment")
async def library_monsters_fragment(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Library monsters fragment."""
    logger.bind(fragment="monsters").debug("LibraryFragmentRequested")
    return await ui.render("site/library/fragments/monsters.html")


@router.get("/library/fragments/monster-clans", name="library_monster_clans_fragment")
async def library_monster_clans_fragment(
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    library_service: Annotated[LibraryFrontendService, Depends(get_library_service)],
    tier: Annotated[str | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
    family: Annotated[str | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
    danger: Annotated[str | None, Query()] = None,
    sort: Annotated[str, Query()] = "tier_title",
    view: Annotated[str, Query()] = "cards",
    q: Annotated[str | None, Query()] = None,
):
    """Render the Library monster clans fragment."""
    logger.bind(fragment="monster-clans").debug("LibraryFragmentRequested")
    result = await library_service.monster_clans(
        tier=tier,
        location=location,
        family=family,
        tag=tag,
        danger=danger,
        sort=sort,
        view=view,
        q=q,
    )
    return await ui.render("site/library/fragments/monster_clans.html", context={"result": result})


@router.get("/library/fragments/monster-clans/{clan_id}", name="library_monster_clan_detail_fragment")
async def library_monster_clan_detail_fragment(
    clan_id: str,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    library_service: Annotated[LibraryFrontendService, Depends(get_library_service)],
):
    """Render a Library monster clan detail fragment."""
    logger.bind(fragment="monster-clan-detail", clan_id=clan_id).debug("LibraryFragmentRequested")
    clan = await library_service.monster_clan_detail(clan_id)
    return await ui.render(
        "site/library/fragments/monster_clan_detail.html",
        context={
            "clan_id": clan_id,
            "clan": clan,
        },
    )
