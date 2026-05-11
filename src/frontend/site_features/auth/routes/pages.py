from contextlib import suppress
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.session.cookies import clear_active_character_cookie
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.forms.login import LoginForm
from src.frontend.site_features.auth.forms.register import RegisterForm
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(tags=["Auth"])


@router.get("/login", name="login")
async def login_page(request: Request, ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    return await ui.render(
        "site/auth/login.html",
        context={
            "form": LoginForm(),
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
        return await ui.render("site/auth/login.html", context={"form": form}, status_code=status.HTTP_400_BAD_REQUEST)

    try:
        tokens = await auth_service.login(form.email, form.password)
        log_debug_payload("auth_page.login_submit", tokens, enabled=settings.debug)
    except httpx.HTTPStatusError:
        form.error = "Incorrect email or password"
        return await ui.render("site/auth/login.html", context={"form": form}, status_code=status.HTTP_401_UNAUTHORIZED)
    except httpx.RequestError:
        return await ui.render(
            "site/auth/login.html",
            context={"form": form, "backend_unavailable": True},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

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
        response = await auth_service.register(form.email, form.password)
        log_debug_payload("auth_page.register_submit", response, enabled=settings.debug)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_409_CONFLICT:
            form.errors.append("Email already registered")
        else:
            form.errors.append("Registration failed, please try again")
        return await ui.render(
            "site/auth/register.html", context={"form": form}, status_code=status.HTTP_400_BAD_REQUEST
        )
    except httpx.RequestError:
        form.errors.append("Game server is starting. Please refresh and try again.")
        return await ui.render(
            "site/auth/register.html", context={"form": form}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
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
    clear_active_character_cookie(response)
    return response
