import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from loguru import logger

from src.frontend.integrations.backend_api.auth import BackendAuthApi, TokenResponse, UserResponse
from src.frontend.site_features.auth.token_state import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, get_access_token


class FrontendAuthService:
    access_cookie_name = ACCESS_COOKIE_NAME
    refresh_cookie_name = REFRESH_COOKIE_NAME

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

    async def refresh(self, refresh_token: str) -> TokenResponse:
        tokens = await self.auth_api.refresh(refresh_token)
        logger.info("Frontend auth refresh completed")
        return tokens

    async def get_current_user(self, request: Request) -> UserResponse | None:
        if getattr(request.state, "user", None) is not None:
            return request.state.user

        access_token = get_access_token(request)
        if not access_token:
            tokens = await self._refresh_from_request(request)
            if not tokens:
                return None
            access_token = tokens.access_token

        user = await self._current_user_or_refresh(request, access_token)
        if user is not None:
            request.state.user = user
            logger.info("Frontend current user resolved: user_id={}", user.id)
        return user

    async def require_current_user(self, request: Request) -> UserResponse:
        user = await self.get_current_user(request)
        if user is None:
            if getattr(request.state, "backend_unavailable", False):
                logger.warning("Frontend auth required while backend is unavailable: path={}", request.url.path)
                raise _backend_starting_redirect()
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

    async def _current_user_or_refresh(self, request: Request, access_token: str) -> UserResponse | None:
        try:
            return await self.auth_api.current_user(access_token)
        except httpx.RequestError as exc:
            request.state.backend_unavailable = True
            logger.warning("Frontend current user lookup backend unavailable: error={}", exc)
            return None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != status.HTTP_401_UNAUTHORIZED:
                logger.warning("Frontend current user lookup rejected: status={}", exc.response.status_code)
                return None

            tokens = await self._refresh_from_request(request)
            if not tokens:
                return None
            try:
                return await self.auth_api.current_user(tokens.access_token)
            except httpx.RequestError as refresh_exc:
                request.state.backend_unavailable = True
                logger.warning("Frontend current user lookup backend unavailable after refresh: error={}", refresh_exc)
                return None
            except httpx.HTTPStatusError as refresh_exc:
                logger.warning(
                    "Frontend current user lookup rejected after refresh: status={}",
                    refresh_exc.response.status_code,
                )
                return None

    async def _refresh_from_request(self, request: Request) -> TokenResponse | None:
        refresh_token = request.cookies.get(self.refresh_cookie_name)
        if not refresh_token:
            return None

        try:
            tokens = await self.refresh(refresh_token)
        except httpx.HTTPStatusError as exc:
            logger.warning("Frontend auth refresh rejected: status={}", exc.response.status_code)
            if exc.response.status_code == status.HTTP_401_UNAUTHORIZED:
                request.state.clear_auth_cookies = True
            return None
        except httpx.RequestError as exc:
            request.state.backend_unavailable = True
            logger.warning("Frontend auth refresh backend unavailable: error={}", exc)
            return None

        request.state.access_token = tokens.access_token
        request.state.auth_tokens = tokens
        return tokens


def _login_redirect() -> HTTPException:
    return HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


def _backend_starting_redirect() -> HTTPException:
    return HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login?server=starting"})
