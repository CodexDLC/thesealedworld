import uuid
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.core.exceptions import AuthException
from src.backend.core.security import decode_access_token
from src.backend.features_site.auth.models import User
from src.backend.features_site.auth.repositories.token_repository import TokenRepository
from src.backend.features_site.auth.repositories.user_repository import UserRepository
from src.backend.features_site.auth.services.auth_service import AuthService
from src.backend.features_site.auth.services.user_cache import AuthUserCache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(session=db)


def get_token_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> TokenRepository:
    return TokenRepository(session=db)


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    token_repository: Annotated[TokenRepository, Depends(get_token_repository)],
) -> AuthService:
    return AuthService(user_repository=user_repository, token_repository=token_repository)


def get_auth_user_cache(request: Request) -> AuthUserCache | None:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return None
    return AuthUserCache(redis=redis)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_cache: Annotated[AuthUserCache | None, Depends(get_auth_user_cache)] = None,
) -> User:
    try:
        payload = decode_access_token(token)
        user_id_raw: Any = payload.get("sub")
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, TypeError) as exc:
        raise AuthException(detail="Could not validate credentials") from exc

    if user_cache is not None:
        cached_user = await user_cache.get(user_id)
        if cached_user is not None:
            return cached_user

    user = await auth_service.user_repository.get_by_id(user_id=user_id)
    if user is None:
        raise AuthException(detail="User not found")
    if user_cache is not None:
        await user_cache.set(user)
    return user
