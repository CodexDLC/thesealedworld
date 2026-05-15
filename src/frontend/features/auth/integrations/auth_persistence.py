from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from src.frontend.features.auth.dto.user import UserCreate
    from src.frontend.features.auth.models import RefreshToken, User
    from src.frontend.features.auth.repositories.token_repository import TokenRepository
    from src.frontend.features.auth.repositories.user_repository import UserRepository


class DuplicateEmailError(ValueError):
    """Raised when auth persistence rejects a duplicate user email."""


@dataclass(slots=True)
class AuthPersistence:
    users: UserRepository
    tokens: TokenRepository

    async def register_user(self, user_in: UserCreate) -> User:
        try:
            user = await self.users.create(user_in)
            await self.users.commit()
        except IntegrityError:
            raise DuplicateEmailError from None
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.users.get_by_email(email)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.users.get_by_id(user_id)

    async def create_refresh_token(self, user_id: uuid.UUID, token: str, expires_at: datetime) -> RefreshToken:
        refresh_token = await self.tokens.create(user_id=user_id, token=token, expires_at=expires_at)
        await self.tokens.commit()
        return refresh_token

    async def delete_refresh_token(self, token: str) -> None:
        await self.tokens.delete(token)
        await self.tokens.commit()

    async def get_refresh_token(self, token: str) -> RefreshToken | None:
        return await self.tokens.get_by_token(token)
