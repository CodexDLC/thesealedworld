from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from src.frontend.config.settings import settings
from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.forms.login import LoginForm
from src.frontend.features.auth.forms.register import RegisterForm
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.features.auth.services.referral_code import normalize_referral_code
from src.frontend.features.auth.token_state import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from src.frontend.game_features.session.cookies import clear_active_character_cookie
from src.frontend.game_features.session.token_state import clear_game_token_cookies
from src.shared.exceptions import AuthException, BusinessLogicException

router = APIRouter(tags=["Auth"])

_REFERRAL_COOKIE_NAME = "tbmmorpg_ref"
_REFERRAL_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


@router.get("/login", name="login")
async def login_page(request: Request, ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    auth_expired = request.query_params.get("expired") == "1"
    response = await ui.render(
        "site/index.html",
        context={
            "form": LoginForm(),
            "auth_overlay_open": True,
            "auth_mode": "login",
            "auth_expired": auth_expired,
            "backend_unavailable": request.query_params.get("server") == "starting"
            or getattr(request.state, "backend_unavailable", False),
        },
    )
    if auth_expired:
        # Hard reset: clear every cookie that could still resolve a user.
        # Without explicit domain= the browser keeps the .thesealed.localhost cookie
        # alongside a now-cleared host-scoped one, so the loop persists.
        cookie_domain = settings.auth_cookie_domain or None
        response.delete_cookie(ACCESS_COOKIE_NAME, domain=cookie_domain)
        response.delete_cookie(REFRESH_COOKIE_NAME, domain=cookie_domain)
        clear_active_character_cookie(response)
        clear_game_token_cookies(response)
    return response


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

    response = RedirectResponse(url="/play", status_code=status.HTTP_303_SEE_OTHER)
    auth_service.attach_auth_cookies(response, tokens)
    return response


@router.get("/register", name="register")
async def register_page(request: Request, ui: Annotated[UIRenderer, Depends(get_ui_renderer)]):
    query_code = normalize_referral_code(request.query_params.get("ref"))
    cookie_code = normalize_referral_code(request.cookies.get(_REFERRAL_COOKIE_NAME))
    initial_code = query_code or cookie_code or ""
    response = await ui.render(
        "site/index.html",
        context={
            "form": RegisterForm(referrer_code=initial_code),
            "auth_overlay_open": True,
            "auth_mode": "register",
        },
    )
    if query_code and query_code != cookie_code:
        response.set_cookie(
            _REFERRAL_COOKIE_NAME,
            query_code,
            max_age=_REFERRAL_COOKIE_MAX_AGE,
            httponly=False,
            samesite="lax",
            secure=settings.auth_cookie_secure,
            path="/",
        )
    return response


@router.post("/register", name="register_submit")
async def register_submit(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
):
    form = await RegisterForm.from_request(request)
    if not form.referrer_code:
        form.referrer_code = normalize_referral_code(request.cookies.get(_REFERRAL_COOKIE_NAME)) or ""
    if not form.is_valid:
        return await ui.render(
            "site/index.html",
            context={"form": form, "auth_overlay_open": True, "auth_mode": "register"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        await auth_service.register(form.email, form.password, referrer_code=form.referrer_code or None)
    except BusinessLogicException:
        form.errors.append("Email already registered")
        return await ui.render(
            "site/index.html",
            context={"form": form, "auth_overlay_open": True, "auth_mode": "register"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(_REFERRAL_COOKIE_NAME, path="/")
    return response


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
