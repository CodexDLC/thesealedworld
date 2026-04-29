import secrets
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.backend.config.settings import settings
from src.backend.core.exceptions import AuthException, BusinessLogicException
from src.backend.core.security import create_access_token, get_password_hash, verify_password
from src.backend.features.auth.dto.token import Token
from src.backend.features.auth.dto.user import UserCreate, UserResponse
from src.backend.features.auth.repositories.token_repository import TokenRepository
from src.backend.features.auth.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repository: UserRepository, token_repository: TokenRepository) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository

    async def register_user(self, user_in: UserCreate) -> UserResponse:
        logger.info(f"AuthService | action=register_attempt email={user_in.email}")
        hashed_password = get_password_hash(user_in.password)
        user_with_hash = user_in.model_copy(update={"password": hashed_password})

        try:
            created_user = await self.user_repository.create(user_with_hash)
            await self.user_repository.commit()
        except IntegrityError:
            raise BusinessLogicException(detail="User with this email already exists") from None

        return UserResponse.model_validate(created_user)

    async def authenticate_user(self, email: str, password: str) -> UserResponse | None:
        user = await self.user_repository.get_by_email(email.strip().lower())
        if not user or not verify_password(password, user.hashed_password) or not user.is_active:
            return None
        return UserResponse.model_validate(user)

    async def create_tokens(self, user: UserResponse) -> Token:
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = secrets.token_urlsafe(32)
        refresh_token_expires = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        await self.token_repository.create(user_id=user.id, token=refresh_token, expires_at=refresh_token_expires)
        await self.token_repository.commit()
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_token(self, token: str) -> Token:
        db_token = await self.token_repository.get_by_token(token)
        if not db_token:
            raise AuthException("Invalid refresh token")

        if db_token.expires_at < datetime.now(UTC):
            await self.token_repository.delete(token)
            await self.token_repository.commit()
            raise AuthException("Refresh token expired")

        user = await self.user_repository.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            await self.token_repository.delete(token)
            await self.token_repository.commit()
            raise AuthException("User not found or inactive")

        await self.token_repository.delete(token)
        user_schema = UserResponse.model_validate(user)
        return await self.create_tokens(user_schema)

    async def logout(self, token: str) -> None:
        await self.token_repository.delete(token)
        await self.token_repository.commit()
