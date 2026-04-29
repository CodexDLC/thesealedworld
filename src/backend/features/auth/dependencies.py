import uuid
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.core.exceptions import AuthException
from src.backend.core.security import decode_access_token
from src.backend.features.auth.models import User
from src.backend.features.auth.repositories.token_repository import TokenRepository
from src.backend.features.auth.repositories.user_repository import UserRepository
from src.backend.features.auth.services.auth_service import AuthService

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


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    try:
        payload = decode_access_token(token)
        user_id_raw: Any = payload.get("sub")
        user_id = uuid.UUID(str(user_id_raw))
    except (ValueError, TypeError) as exc:
        raise AuthException(detail="Could not validate credentials") from exc

    user = await auth_service.user_repository.get_by_id(user_id=user_id)
    if user is None:
        raise AuthException(detail="User not found")
    return user
