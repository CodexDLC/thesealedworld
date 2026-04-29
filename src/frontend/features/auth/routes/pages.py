from contextlib import suppress
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.forms.login import LoginForm
from src.frontend.features.auth.forms.register import RegisterForm
from src.frontend.features.auth.services.auth_service import FrontendAuthService

router = APIRouter(tags=["Auth"])


@router.get("/login", name="login")
async def login_page(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    return await ui.render("site/auth/login.html", context={"form": LoginForm()})


@router.post("/login", name="login_submit")
async def login_submit(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    form = await LoginForm.from_request(request)
    if not form.is_valid:
        return await ui.render("site/auth/login.html", context={"form": form}, status_code=status.HTTP_400_BAD_REQUEST)

    try:
        tokens = await auth_service.login(form.email, form.password)
    except httpx.HTTPStatusError:
        form.error = "Incorrect email or password"
        return await ui.render("site/auth/login.html", context={"form": form}, status_code=status.HTTP_401_UNAUTHORIZED)

    response = RedirectResponse(url="/game-lobby", status_code=status.HTTP_303_SEE_OTHER)
    auth_service.attach_auth_cookies(response, tokens)
    return response


@router.get("/register", name="register")
async def register_page(ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    return await ui.render("site/auth/register.html", context={"form": RegisterForm()})


@router.post("/register", name="register_submit")
async def register_submit(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    form = await RegisterForm.from_request(request)
    if not form.is_valid:
        return await ui.render(
            "site/auth/register.html", context={"form": form}, status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        await auth_service.register(form.email, form.password)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_409_CONFLICT:
            form.errors.append("Email already registered")
        else:
            form.errors.append("Registration failed, please try again")
        return await ui.render(
            "site/auth/register.html", context={"form": form}, status_code=status.HTTP_400_BAD_REQUEST
        )

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", name="logout")
async def logout(
    request: Request,
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    refresh_token = request.cookies.get(auth_service.refresh_cookie_name)
    if refresh_token:
        with suppress(httpx.HTTPError):
            await auth_service.logout(refresh_token)

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    auth_service.clear_auth_cookies(response)
    return response
