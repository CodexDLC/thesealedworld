from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.config.settings import settings
from src.frontend.core.database import get_db
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.account.services.account_service import AccountService
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.features.email.config import get_email_service
from src.frontend.features.public_site.services import build_play_url
from src.frontend.game_features.game_lobby.dependencies.providers import get_game_lobby_page_service
from src.frontend.game_features.game_lobby.view_models.lobby import GameLobbyPageVM, build_lobby_page_vm
from src.shared.utils.url import build_public_base_url

router = APIRouter(prefix="/account", tags=["Account"])

ACCOUNT_PROFILE_SECTIONS = {
    "overview",
    "profile",
    "characters",
    "referrals",
    "payments",
    "security",
    "settings",
}


@router.get("", name="account_root")
async def account_root():
    return RedirectResponse(url="/account/profile", status_code=303)


@router.get("/profile", name="account_profile")
async def account_profile(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    applied = request.query_params.get("applied") == "1"
    active_section = request.query_params.get("section") or "overview"
    if active_section not in ACCOUNT_PROFILE_SECTIONS:
        active_section = "overview"

    repo = UserRepository(session=db)
    stats = await repo.get_referral_stats(user.id)
    referral_users = await repo.list_referrals(user.id, limit=20) if active_section == "referrals" else []
    site_base_url = settings.site_base_url.rstrip("/") if settings.site_base_url else str(request.base_url).rstrip("/")
    service = AccountService()
    profile = service.build_profile_vm(
        user,
        site_base_url=site_base_url,
        referral_stats=stats,
        referral_users=referral_users,
        email_verification_enabled=settings.enable_email_verification,
    )

    lobby = await _load_characters_lobby(request, user) if active_section == "characters" else None

    return await ui.render(
        "account/profile.html",
        context={
            "profile": profile,
            "applied": applied,
            "active_section": active_section,
            "characters_lobby": lobby,
            "play_lobby_url": _play_lobby_url(request),
        },
    )


async def _load_characters_lobby(request: Request, user) -> GameLobbyPageVM | None:
    try:
        service = get_game_lobby_page_service(request)
        response = await service.get_view(user)
        return build_lobby_page_vm(response)
    except Exception:
        logger.bind(user_id=str(getattr(user, "id", ""))).warning("AccountCharactersSummaryUnavailable")
        return None


def _play_lobby_url(request: Request) -> str:
    site_base_url = build_public_base_url(
        configured_base_url=settings.site_base_url,
        domain_name=str(getattr(settings, "domain_name", "") or ""),
        request_base_url=str(request.base_url),
    )
    return_to = f"{site_base_url}{request.url.path}"
    if request.url.query:
        return_to = f"{return_to}?{request.url.query}"
    return build_play_url(f"/game-lobby?{urlencode({'return_to': return_to})}")


@router.post("/apply-tester", name="account_apply_tester")
async def apply_tester(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    repo = UserRepository(session=db)
    service = AccountService(repo=repo, email_service=get_email_service(), email_admin=settings.email_admin)
    try:
        await service.apply_for_testing(user.id)
    except Exception:
        return RedirectResponse(url="/account/profile", status_code=303)

    return RedirectResponse(url="/account/profile?applied=1", status_code=303)
