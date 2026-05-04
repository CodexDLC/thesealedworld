import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from loguru import logger

from src.frontend.integrations.backend_api.auth import BackendAuthApi, TokenResponse, UserResponse


class FrontendAuthService:
    access_cookie_name = "tbmmorpg_access_token"
    refresh_cookie_name = "tbmmorpg_refresh_token"

    def __init__(self, auth_api: BackendAuthApi) -> None:
        self.auth_api = auth_api

    async def login(self, email: str, password: str) -> TokenResponse:
        tokens = await self.auth_api.login(email=email, password=password)
        logger.info("Frontend auth login completed")
        return tokens

    async def register(self, email: str, password: str) -> UserResponse:
        user = await self.auth_api.register(email=email, password=password)
        logger.info("Frontend auth registration completed: user_id={}", user.id)
        return user

    async def logout(self, refresh_token: str) -> None:
        await self.auth_api.logout(refresh_token)
        logger.info("Frontend auth logout completed")

    async def get_current_user(self, request: Request) -> UserResponse | None:
        access_token = request.cookies.get(self.access_cookie_name)
        if not access_token:
            return None
        try:
            user = await self.auth_api.current_user(access_token)
            logger.info("Frontend current user resolved: user_id={}", user.id)
            return user
        except httpx.HTTPStatusError as exc:
            logger.warning("Frontend current user lookup rejected: status={}", exc.response.status_code)
            return None

    async def require_current_user(self, request: Request) -> UserResponse:
        user = await self.get_current_user(request)
        if user is None:
            logger.warning("Frontend auth required: redirecting_to_login path={}", request.url.path)
            raise _login_redirect()
        return user

    def attach_auth_cookies(self, response: Response, tokens: TokenResponse) -> None:
        response.set_cookie(
            self.access_cookie_name,
            tokens.access_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 30,
        )
        response.set_cookie(
            self.refresh_cookie_name,
            tokens.refresh_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 30,
        )

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(self.access_cookie_name)
        response.delete_cookie(self.refresh_cookie_name)


def _login_redirect() -> HTTPException:
    return HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
