from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.config.settings import settings
from src.frontend.core.database import get_db
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.account.services.account_service import AccountService
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.features.email.config import get_email_service

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

    repo = UserRepository(session=db)
    stats = await repo.get_referral_stats(user.id)
    site_base_url = str(request.base_url).rstrip("/")
    service = AccountService()
    profile = service.build_profile_vm(
        user,
        site_base_url=site_base_url,
        referral_stats=stats,
        email_verification_enabled=settings.enable_email_verification,
    )
    applied = request.query_params.get("applied") == "1"
    active_section = request.query_params.get("section") or "overview"
    if active_section not in ACCOUNT_PROFILE_SECTIONS:
        active_section = "overview"

    return await ui.render(
        "account/profile.html",
        context={"profile": profile, "applied": applied, "active_section": active_section},
    )


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
