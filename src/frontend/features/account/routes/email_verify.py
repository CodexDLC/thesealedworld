from __future__ import annotations

from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.core.database import get_db
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.account.services.email_verification_service import (
    PURPOSE_CHANGE,
    PURPOSE_VERIFY,
    EmailVerificationService,
)
from src.frontend.features.auth.repositories.token_repository import TokenRepository
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.features.email.config import get_email_service
from src.shared.exceptions import AuthException, BusinessLogicException

router = APIRouter(tags=["AccountEmail"])


def _build_service(request: Request, db: AsyncSession) -> EmailVerificationService:
    return EmailVerificationService(
        session=db,
        users=UserRepository(session=db),
        tokens=TokenRepository(session=db),
        email_service=get_email_service(),
        site_base_url=str(request.base_url).rstrip("/"),
    )


async def _form_data(request: Request) -> dict[str, str]:
    raw = (await request.body()).decode("utf-8")
    return {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}


@router.post("/account/security/email/verify", name="account_email_verify_start")
async def start_verify(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if user.email_verified_at is not None:
        return RedirectResponse(url="/account/profile?section=security&verify=already", status_code=303)

    users = UserRepository(session=db)
    db_user = await users.get_by_id(user.id)
    if db_user is None:
        return RedirectResponse(url="/login", status_code=303)
    service = _build_service(request, db)
    await service.start_verify_current(db_user)
    return RedirectResponse(url="/account/profile?section=security&verify=sent", status_code=303)


@router.post("/account/security/email/change", name="account_email_change_start")
async def start_change(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    user = getattr(request.state, "user", None)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    payload = await _form_data(request)
    new_email = payload.get("new_email", "").strip().lower()
    current_password = payload.get("current_password", "")

    users = UserRepository(session=db)
    db_user = await users.get_by_id(user.id)
    if db_user is None:
        return RedirectResponse(url="/login", status_code=303)
    service = _build_service(request, db)
    try:
        await service.start_change_email(db_user, new_email, current_password)
    except AuthException:
        return RedirectResponse(url="/account/profile?section=security&change=password", status_code=303)
    except BusinessLogicException:
        return RedirectResponse(url="/account/profile?section=security&change=email", status_code=303)
    return RedirectResponse(url="/account/profile?section=security&change=sent", status_code=303)


@router.get("/account/email/verify/{token}", name="account_email_verify_preview")
async def verify_preview(
    request: Request,
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    service = _build_service(request, db)
    row = await service.lookup(token, PURPOSE_VERIFY)
    return await ui.render(
        "account/email_confirm.html",
        context={
            "purpose": "verify",
            "token": token,
            "row": row,
            "action_url": f"/account/email/verify/{token}/confirm",
        },
    )


@router.post("/account/email/verify/{token}/confirm", name="account_email_verify_confirm")
async def verify_confirm(
    request: Request,
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    service = _build_service(request, db)
    try:
        await service.consume(token, PURPOSE_VERIFY)
    except BusinessLogicException:
        return await ui.render(
            "account/email_confirm.html",
            context={"purpose": "verify", "token": token, "row": None, "failed": True},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/account/profile?section=security&verify=ok", status_code=303)


@router.get("/account/email/change/{token}", name="account_email_change_preview")
async def change_preview(
    request: Request,
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    service = _build_service(request, db)
    row = await service.lookup(token, PURPOSE_CHANGE)
    return await ui.render(
        "account/email_confirm.html",
        context={
            "purpose": "change",
            "token": token,
            "row": row,
            "action_url": f"/account/email/change/{token}/confirm",
        },
    )


@router.post("/account/email/change/{token}/confirm", name="account_email_change_confirm")
async def change_confirm(
    request: Request,
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
):
    service = _build_service(request, db)
    try:
        await service.consume(token, PURPOSE_CHANGE)
    except BusinessLogicException:
        return await ui.render(
            "account/email_confirm.html",
            context={"purpose": "change", "token": token, "row": None, "failed": True},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/login?email_changed=1", status_code=303)
