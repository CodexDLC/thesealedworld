from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.forms.login import LoginForm
from src.frontend.features.auth.forms.register import RegisterForm
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.session.cookies import clear_active_character_cookie
from src.shared.exceptions import AuthException, BusinessLogicException

router = APIRouter(tags=["Auth"])


@router.get("/login", name="login")
async def login_page(request: Request, ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    return await ui.render(
        "site/index.html",
        context={
            "form": LoginForm(),
            "auth_overlay_open": True,
            "auth_mode": "login",
            "backend_unavailable": request.query_params.get("server") == "starting"
            or getattr(request.state, "backend_unavailable", False),
        },
    )


@router.post("/login", name="login_submit")
async def login_submit(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    form = await LoginForm.from_request(request)
    if not form.is_valid:
        return await ui.render(
            "site/index.html",
            context={"form": form, "auth_overlay_open": True, "auth_mode": "login"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        tokens = await auth_service.login(form.email, form.password)
    except AuthException:
        form.error = "Incorrect email or password"
        return await ui.render(
            "site/index.html",
            context={"form": form, "auth_overlay_open": True, "auth_mode": "login"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse(url="/game-lobby", status_code=status.HTTP_303_SEE_OTHER)
    auth_service.attach_auth_cookies(response, tokens)
    return response


@router.get("/register", name="register")
async def register_page(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    return await ui.render(
        "site/index.html",
        context={"form": RegisterForm(), "auth_overlay_open": True, "auth_mode": "register"},
    )


@router.post("/register", name="register_submit")
async def register_submit(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    form = await RegisterForm.from_request(request)
    if not form.is_valid:
        return await ui.render(
            "site/index.html",
            context={"form": form, "auth_overlay_open": True, "auth_mode": "register"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        await auth_service.register(form.email, form.password)
    except BusinessLogicException:
        form.errors.append("Email already registered")
        return await ui.render(
            "site/index.html",
            context={"form": form, "auth_overlay_open": True, "auth_mode": "register"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", name="logout")
async def logout(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    refresh_token = request.cookies.get(auth_service.refresh_cookie_name)
    if refresh_token:
        with suppress(AuthException):
            await auth_service.logout(refresh_token)

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    auth_service.clear_auth_cookies(response)
    clear_active_character_cookie(response)
    return response
