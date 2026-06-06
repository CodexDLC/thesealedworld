import uuid

from fastapi import HTTPException, Request, status
from fastapi.responses import Response
from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.features.auth.dto.token import Token as TokenResponse
from src.frontend.features.auth.dto.user import UserCreate, UserResponse
from src.frontend.features.auth.security import decode_access_token
from src.frontend.features.auth.services.site_auth_service import (
    AuthService,
    RefreshTokenNotFoundError,
)
from src.frontend.features.auth.token_state import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, get_access_token
from src.shared.exceptions import AuthException


class FrontendAuthService:
    access_cookie_name = ACCESS_COOKIE_NAME
    refresh_cookie_name = REFRESH_COOKIE_NAME

    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.auth_service.authenticate_user(email, password)
        if user is None:
            raise AuthException(detail="Incorrect email or password")
        tokens = await self.auth_service.create_tokens(user)
        logger.info("FrontendAuthLoginCompleted")
        return tokens

    async def register(self, email: str, password: str, *, referrer_code: str | None = None) -> UserResponse:
        user = await self.auth_service.register_user(
            UserCreate(email=email, password=password, referrer_code=referrer_code)
        )
        logger.bind(user_id=str(user.id)).info("FrontendAuthRegistrationCompleted")
        return user

    async def logout(self, refresh_token: str) -> None:
        await self.auth_service.logout(refresh_token)
        logger.info("FrontendAuthLogoutCompleted")

    async def refresh(self, refresh_token: str) -> TokenResponse:
        tokens = await self.auth_service.refresh_token(refresh_token)
        logger.debug("FrontendAuthRefreshCompleted")
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
            logger.bind(user_id=str(user.id)).debug("FrontendCurrentUserResolved")
        return user

    async def require_current_user(self, request: Request) -> UserResponse:
        user = await self.get_current_user(request)
        if user is None:
            if getattr(request.state, "backend_unavailable", False):
                logger.bind(path=request.url.path).warning("FrontendAuthRequiredBackendUnavailable")
                raise _backend_starting_redirect()
            logger.bind(path=request.url.path).warning("FrontendAuthRequired")
            raise _login_redirect()
        return user

    def attach_auth_cookies(self, response: Response, tokens: TokenResponse) -> None:
        cookie_domain = settings.auth_cookie_domain or None
        response.set_cookie(
            self.access_cookie_name,
            tokens.access_token,
            httponly=True,
            samesite="lax",
            secure=settings.auth_cookie_secure,
            max_age=60 * 30,
            domain=cookie_domain,
        )
        response.set_cookie(
            self.refresh_cookie_name,
            tokens.refresh_token,
            httponly=True,
            samesite="lax",
            secure=settings.auth_cookie_secure,
            max_age=60 * 60 * 24 * 30,
            domain=cookie_domain,
        )

    def clear_auth_cookies(self, response: Response) -> None:
        cookie_domain = settings.auth_cookie_domain or None
        response.delete_cookie(self.access_cookie_name, domain=cookie_domain)
        response.delete_cookie(self.refresh_cookie_name, domain=cookie_domain)

    async def _current_user_or_refresh(self, request: Request, access_token: str) -> UserResponse | None:
        try:
            payload = decode_access_token(access_token)
            user_id = uuid.UUID(str(payload.get("sub")))
            user = await self.auth_service.get_user_by_id(user_id)
            return UserResponse.model_validate(user) if user is not None else None
        except (AuthException, ValueError, TypeError) as exc:
            logger.bind(error=str(exc)).warning("FrontendCurrentUserLookupRejected")
            tokens = await self._refresh_from_request(request)
            if not tokens:
                return None
            try:
                payload = decode_access_token(tokens.access_token)
                user = await self.auth_service.get_user_by_id(uuid.UUID(str(payload.get("sub"))))
                return UserResponse.model_validate(user) if user is not None else None
            except Exception as refresh_exc:
                logger.bind(error=str(refresh_exc)).warning("FrontendCurrentUserLookupRejectedAfterRefresh")
                return None
        except Exception:
            tokens = await self._refresh_from_request(request)
            if not tokens:
                return None
            try:
                payload = decode_access_token(tokens.access_token)
                user = await self.auth_service.get_user_by_id(uuid.UUID(str(payload.get("sub"))))
                return UserResponse.model_validate(user) if user is not None else None
            except Exception as refresh_exc:
                logger.bind(error=str(refresh_exc)).warning("FrontendCurrentUserLookupRejectedAfterRefresh")
                return None

    async def _refresh_from_request(self, request: Request) -> TokenResponse | None:
        refresh_token = request.cookies.get(self.refresh_cookie_name)
        if not refresh_token:
            return None

        try:
            tokens = await self.refresh(refresh_token)
        except RefreshTokenNotFoundError as exc:
            # Likely a rotation race: a sibling request already consumed the cookie.
            # Stay silent — do NOT clear cookies. The next refresh attempt either
            # succeeds with the freshly issued cookie or falls into the hard branch.
            logger.bind(error=str(exc), recovered_from="race").info("FrontendAuthRefreshRaceDetected")
            return None
        except AuthException as exc:
            logger.bind(error=str(exc)).warning("FrontendAuthRefreshRejected")
            request.state.clear_auth_cookies = True
            return None

        request.state.access_token = tokens.access_token
        request.state.auth_tokens = tokens
        return tokens


def _login_redirect() -> HTTPException:
    return HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


def _backend_starting_redirect() -> HTTPException:
    return HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login?server=starting"})
