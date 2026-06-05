from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.frontend.features.auth.models import ReferralReward
from src.frontend.features.auth.services.referral_code import generate_referral_code, normalize_referral_code

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from src.frontend.features.auth.dto.user import UserCreate
    from src.frontend.features.auth.models import RefreshToken, User
    from src.frontend.features.auth.repositories.token_repository import TokenRepository
    from src.frontend.features.auth.repositories.user_repository import UserRepository


class DuplicateEmailError(ValueError):
    """Raised when auth persistence rejects a duplicate user email."""


_REFERRAL_CODE_RETRY_LIMIT = 5


@dataclass(slots=True)
class AuthPersistence:
    users: UserRepository
    tokens: TokenRepository

    async def register_user(self, user_in: UserCreate) -> User:
        referrer = await self._resolve_referrer(getattr(user_in, "referrer_code", None))
        last_error: IntegrityError | None = None
        for _ in range(_REFERRAL_CODE_RETRY_LIMIT):
            code = generate_referral_code()
            try:
                user = await self.users.create(
                    user_in,
                    referral_code=code,
                    referred_by_id=referrer.id if referrer is not None else None,
                )
                if referrer is not None:
                    self.users.session.add(ReferralReward(referrer_id=referrer.id, referee_id=user.id, kind="signup"))
                await self.users.commit()
                return user
            except IntegrityError as exc:
                last_error = exc
                await self.users.session.rollback()
                message = str(exc.orig).lower() if exc.orig else str(exc).lower()
                if "auth_users_email" in message or "email" in message:
                    raise DuplicateEmailError from None
                if "referral_code" not in message:
                    raise
                # Else: code collided — try again.
        logger.bind(error=str(last_error)).error("ReferralCodeRetryExhausted")
        raise RuntimeError("Could not allocate a unique referral code")

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

    async def _resolve_referrer(self, raw_code: str | None) -> User | None:
        normalized = normalize_referral_code(raw_code)
        if normalized is None:
            return None
        return await self.users.get_by_referral_code(normalized)
