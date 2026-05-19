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


@router.get("", name="account_root")
async def account_root():
    return RedirectResponse(url="/account/profile", status_code=307)


@router.get("/profile", name="account_profile")
async def account_profile(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    service = AccountService()
    profile = service.build_profile_vm(user)
    applied = request.query_params.get("applied") == "1"

    return await ui.render(
        "account/profile.html",
        context={"profile": profile, "applied": applied},
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
