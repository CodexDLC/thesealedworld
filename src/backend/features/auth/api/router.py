from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.backend.config.settings import settings
from src.backend.core.exceptions import AuthException
from src.backend.features.auth.dependencies import get_auth_service, get_current_user
from src.backend.features.auth.dto.token import RefreshTokenRequest, Token
from src.backend.features.auth.dto.user import UserCreate, UserResponse
from src.backend.features.auth.models import User
from src.backend.features.auth.services.auth_service import AuthService
from src.shared.utils.dev_utils import log_debug_payload

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_new_user(
    user_in: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    response = await auth_service.register_user(user_in)
    log_debug_payload("auth.register", response, enabled=settings.debug)
    return response


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Token:
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise AuthException(detail="Incorrect email or password")
    response = await auth_service.create_tokens(user)
    log_debug_payload("auth.login", response, enabled=settings.debug)
    return response


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    response = UserResponse.model_validate(current_user)
    log_debug_payload("auth.me", response, enabled=settings.debug)
    return response


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_in: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Token:
    response = await auth_service.refresh_token(token_in.refresh_token)
    log_debug_payload("auth.refresh", response, enabled=settings.debug)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token_in: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await auth_service.logout(token_in.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
