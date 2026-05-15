from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

from src.frontend.config.settings import settings
from src.frontend.features.auth.dto.token import Token
from src.frontend.features.auth.dto.user import UserCreate, UserResponse
from src.frontend.features.auth.integrations import DuplicateEmailError
from src.frontend.features.auth.security import create_access_token
from src.frontend.features.auth.security.passwords import get_password_hash, verify_password
from src.shared.exceptions import AuthException, BusinessLogicException

if TYPE_CHECKING:
    import uuid

    from src.frontend.features.auth.integrations import AuthPersistence
    from src.frontend.features.auth.models import User


class AuthService:
    def __init__(self, persistence: AuthPersistence) -> None:
        self._persistence = persistence

    async def register_user(self, user_in: UserCreate) -> UserResponse:
        logger.info("Auth registration started")
        hashed_password = get_password_hash(user_in.password)
        user_with_hash = user_in.model_copy(update={"password": hashed_password})

        try:
            created_user = await self._persistence.register_user(user_with_hash)
        except DuplicateEmailError:
            logger.warning("Auth registration rejected: duplicate_email")
            raise BusinessLogicException(detail="User with this email already exists") from None

        logger.info("Auth registration completed: user_id={}", created_user.id)
        return UserResponse.model_validate(created_user)

    async def authenticate_user(self, email: str, password: str) -> UserResponse | None:
        user = await self._persistence.get_user_by_email(email.strip().lower())
        if not user or not verify_password(password, user.hashed_password) or not user.is_active:
            logger.warning("Auth login rejected: invalid_credentials_or_inactive_user")
            return None
        logger.info("Auth login accepted: user_id={}", user.id)
        return UserResponse.model_validate(user)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._persistence.get_user_by_id(user_id)

    async def create_tokens(self, user: UserResponse) -> Token:
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = secrets.token_urlsafe(32)
        refresh_token_expires = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        await self._persistence.create_refresh_token(
            user_id=user.id,
            token=refresh_token,
            expires_at=refresh_token_expires,
        )
        logger.info("Auth tokens issued: user_id={} refresh_expires_at={}", user.id, refresh_token_expires.isoformat())
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")  # nosec

    async def refresh_token(self, token: str) -> Token:
        db_token = await self._persistence.get_refresh_token(token)
        if not db_token:
            logger.warning("Auth refresh rejected: token_not_found")
            raise AuthException("Invalid refresh token")

        if db_token.expires_at < datetime.now(UTC):
            await self._persistence.delete_refresh_token(token)
            logger.warning("Auth refresh rejected: token_expired user_id={}", db_token.user_id)
            raise AuthException("Refresh token expired")

        user = await self.get_user_by_id(db_token.user_id)
        if not user or not user.is_active:
            await self._persistence.delete_refresh_token(token)
            logger.warning("Auth refresh rejected: user_missing_or_inactive user_id={}", db_token.user_id)
            raise AuthException("User not found or inactive")

        await self._persistence.delete_refresh_token(token)
        user_schema = UserResponse.model_validate(user)
        logger.info("Auth refresh accepted: user_id={}", user.id)
        return await self.create_tokens(user_schema)

    async def logout(self, token: str) -> None:
        await self._persistence.delete_refresh_token(token)
        logger.info("Auth logout completed")
