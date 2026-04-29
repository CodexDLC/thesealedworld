from typing import Annotated

from fastapi import APIRouter, Depends

from src.frontend.core.renderer import UIRenderer, get_ui_renderer

router = APIRouter(tags=["Frontend Pages"])


@router.get("/", name="index")
async def index(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Root endpoint rendering the landing page."""
    return await ui.render("site/index.html")


@router.get("/system/design", name="design_system")
async def design_system(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Design System page using the new UIRenderer."""
    return await ui.render("system/design_system.html")


@router.get("/about", name="about")
async def about(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the About page."""
    return await ui.render("site/about.html")


@router.get("/library", name="library")
async def library(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Library placeholder page."""
    return await ui.render("site/library.html")


@router.get("/news", name="news")
async def news(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the News placeholder page."""
    return await ui.render("site/news.html")


@router.get("/game/select-character", name="select_character")
async def select_character_page(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Character Selection page."""
    return await ui.render("game/select_character.html")


@router.get("/game", name="game")
async def game_page(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Game page."""
    return await ui.render("game/index.html")
