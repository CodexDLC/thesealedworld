import uuid
from typing import Annotated, Any

import httpx
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.core.database import get_db
from src.frontend.features.auth.integrations import AuthPersistence
from src.frontend.features.auth.models import User
from src.frontend.features.auth.repositories.token_repository import TokenRepository
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.features.auth.security import decode_access_token
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.features.auth.services.site_auth_service import AuthService
from src.shared.exceptions import AuthException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_backend_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.backend_http_client


def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(session=db)


def get_token_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> TokenRepository:
    return TokenRepository(session=db)


def get_site_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    token_repository: Annotated[TokenRepository, Depends(get_token_repository)],
) -> AuthService:
    return AuthService(persistence=AuthPersistence(user_repository, token_repository))


get_auth_service = get_site_auth_service


def get_frontend_auth_service(
    site_auth_service: Annotated[AuthService, Depends(get_site_auth_service)],
) -> FrontendAuthService:
    return FrontendAuthService(auth_service=site_auth_service)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_site_auth_service)],
) -> User:
    try:
        payload = decode_access_token(token)
        user_id_raw: Any = payload.get("sub")
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, TypeError) as exc:
        raise AuthException(detail="Could not validate credentials") from exc

    user = await auth_service.get_user_by_id(user_id=user_id)
    if user is None:
        raise AuthException(detail="User not found")
    return user
