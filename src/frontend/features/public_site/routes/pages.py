from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, Response

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.shared.utils.url import build_public_base_url

router = APIRouter(tags=["Frontend Pages"])


@router.get("/", name="index")
async def index(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Root endpoint rendering the landing page."""
    return await ui.render(
        "site/index.html",
        context={
            "meta": {
                "title": "The Sealed World - Запечатанный мир",
                "description": "Браузерная MMORPG об опасных вылазках за стену, добыче и возвращении домой живым.",
                "url": "/",
                "image": "/static/images/site/the-sealed-world/hero-main.webp",
            }
        },
    )


@router.get("/system/design", name="design_system")
async def design_system(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Design System page using the new UIRenderer."""
    return await ui.render("system/design_system.html")


@router.get("/about", name="about")
async def about(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the About page."""
    return await ui.render(
        "site/about.html",
        context={
            "meta": {
                "title": "О проекте - The Sealed World",
                "description": "Лор, сеттинг и основные идеи мира The Sealed World.",
                "url": "/about",
            }
        },
    )


# ── SEO / Crawler Layer ──


_ROBOTS_TXT = """\
User-agent: *
Allow: /
Allow: /about
Allow: /news
Allow: /library

Disallow: /login
Disallow: /register
Disallow: /logout
Disallow: /account
Disallow: /admin
Disallow: /game-lobby
Disallow: /game
Disallow: /api
Disallow: /system
Disallow: /survey
Disallow: /health
Disallow: /static

Sitemap: {base}/sitemap.xml
"""

_LLMS_TXT = """\
# The Sealed World

> Browser-based turn-based MMORPG about dangerous expeditions beyond the wall, \
loot, and making it home alive.

The Sealed World (Запечатанный мир) is a browser-based multiplayer RPG \
currently in pre-alpha testing.

## Core Loop

- Create a character and enter a sealed city
- Venture beyond the wall on turn-based expeditions
- Fight monsters, gather loot, level up
- Return to the city to trade, craft, and prepare

## Pages

- Landing: /
- About: /about
- News: /news
- Library (game lore & bestiary): /library

## Status

Pre-alpha. Recruiting testers.
"""


@router.get("/robots.txt", name="robots_txt")
async def robots_txt(request: Request) -> PlainTextResponse:
    base = _public_base_url(request)
    return PlainTextResponse(_ROBOTS_TXT.format(base=base))


@router.get("/llms.txt", name="llms_txt")
async def llms_txt() -> PlainTextResponse:
    return PlainTextResponse(_LLMS_TXT)


_SITEMAP_PATHS = ("/", "/about", "/news", "/library")


@router.get("/sitemap.xml", name="sitemap_xml")
async def sitemap_xml(request: Request) -> Response:
    base = _public_base_url(request)
    urls = "\n".join(f"  <url><loc>{base}{path}</loc></url>" for path in _SITEMAP_PATHS)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")


def _public_base_url(request: Request) -> str:
    return build_public_base_url(
        configured_base_url=settings.site_base_url,
        domain_name=str(getattr(settings, "domain_name", "") or ""),
        request_base_url=str(request.base_url),
    )
