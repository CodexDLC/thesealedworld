from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.features.public_site.services import PlayAvailabilityService, build_play_url
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
                "image": settings.site_meta_image,
            }
        },
    )


@router.get("/play", name="play_entry")
async def play_entry(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    if not await PlayAvailabilityService().is_available():
        return await ui.render(
            "site/play_unavailable.html",
            context={
                "meta": {
                    "title": "Игровой сервер недоступен - The Sealed World",
                    "description": "Игровой слой The Sealed World временно недоступен из-за технического обслуживания.",
                    "url": "/play",
                    "robots": "noindex, nofollow",
                }
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    user = await auth_service.get_current_user(request)
    if user is None:
        return await ui.render("site/index.html", context={"auth_overlay_open": True, "auth_mode": "login"})

    query = urlencode({"return_to": f"{_public_base_url(request)}/"})
    return RedirectResponse(build_play_url(f"/game-lobby?{query}"), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/system/design", name="design_system")
async def design_system(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the Design System page using the new UIRenderer."""
    return await ui.render("system/design_system.html")


@router.get("/about", name="about", include_in_schema=False)
async def about() -> RedirectResponse:
    """The standalone About page was retired; lore lives in /library now."""
    return RedirectResponse(url="/library", status_code=301)


@router.get("/support", name="support")
async def support(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    """Render the public support and tester feedback hub."""
    return await ui.render(
        "site/support.html",
        context={
            "meta": {
                "title": "Поддержка и обратная связь - The Sealed World",
                "description": "Сообщить о баге, оценить баланс, темп боя, понятность интерфейса или предложить идею для вылазок.",
                "url": "/support",
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
Allow: /support

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
- Support and feedback: /support

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


_SITEMAP_PATHS = ("/", "/about", "/news", "/library", "/support")


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
