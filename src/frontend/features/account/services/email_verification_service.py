from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select, update

from src.frontend.features.auth.models import EmailVerificationToken, User
from src.frontend.features.auth.security.passwords import verify_password
from src.shared.exceptions import AuthException, BusinessLogicException

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.frontend.features.auth.repositories.token_repository import TokenRepository
    from src.frontend.features.auth.repositories.user_repository import UserRepository
    from src.frontend.features.email.services.email_service import EmailService

PURPOSE_VERIFY = "verify_current"
PURPOSE_CHANGE = "change_email"
_TOKEN_TTL = timedelta(hours=24)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class EmailVerificationService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        tokens: TokenRepository,
        email_service: EmailService,
        *,
        site_base_url: str,
    ) -> None:
        self._session = session
        self._users = users
        self._tokens = tokens
        self._email = email_service
        self._site_base_url = site_base_url.rstrip("/")

    async def start_verify_current(self, user: User) -> None:
        token = await self._issue_token(user.id, PURPOSE_VERIFY, new_email=None)
        link = f"{self._site_base_url}/account/email/verify/{token}"
        await self._email.send_template(
            to=user.email,
            subject="Подтверждение почты",
            template="email_verify_current.html",
            email=user.email,
            link=link,
        )

    async def start_change_email(self, user: User, new_email: str, current_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise AuthException(detail="Incorrect password")
        normalized = new_email.strip().lower()
        if "@" not in normalized:
            raise BusinessLogicException(detail="Invalid new email")
        existing = await self._users.get_by_email(normalized)
        if existing is not None:
            raise BusinessLogicException(detail="Email already in use")
        token = await self._issue_token(user.id, PURPOSE_CHANGE, new_email=normalized)
        link = f"{self._site_base_url}/account/email/change/{token}"
        await self._email.send_template(
            to=normalized,
            subject="Подтверждение смены почты",
            template="email_change_confirm.html",
            email=normalized,
            link=link,
        )

    async def lookup(self, token: str, purpose: str) -> EmailVerificationToken | None:
        result = await self._session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == _hash_token(token),
                EmailVerificationToken.purpose == purpose,
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, token: str, purpose: str) -> User:
        row = await self.lookup(token, purpose)
        now = datetime.now(UTC)
        if row is None or row.consumed_at is not None or row.expires_at < now:
            raise BusinessLogicException(detail="Token invalid or expired")

        user = await self._users.get_by_id(row.user_id)
        if user is None:
            raise BusinessLogicException(detail="User not found")

        if purpose == PURPOSE_VERIFY:
            await self._session.execute(update(User).where(User.id == user.id).values(email_verified_at=now))
        elif purpose == PURPOSE_CHANGE:
            if not row.new_email:
                raise BusinessLogicException(detail="Token has no target email")
            duplicate = await self._users.get_by_email(row.new_email)
            if duplicate is not None and duplicate.id != user.id:
                raise BusinessLogicException(detail="Email already in use")
            await self._session.execute(
                update(User).where(User.id == user.id).values(email=row.new_email, email_verified_at=now)
            )
            await self._tokens.delete_all_for_user(user.id)
        else:
            raise BusinessLogicException(detail="Unknown purpose")

        await self._session.execute(
            update(EmailVerificationToken).where(EmailVerificationToken.id == row.id).values(consumed_at=now)
        )
        await self._session.commit()
        refreshed = await self._users.get_by_id(user.id)
        assert refreshed is not None
        logger.bind(user_id=str(user.id), purpose=purpose).info("EmailVerificationConsumed")
        return refreshed

    async def _issue_token(self, user_id: uuid.UUID, purpose: str, *, new_email: str | None) -> str:
        plain = secrets.token_urlsafe(32)
        row = EmailVerificationToken(
            user_id=user_id,
            purpose=purpose,
            new_email=new_email,
            token_hash=_hash_token(plain),
            expires_at=datetime.now(UTC) + _TOKEN_TTL,
        )
        self._session.add(row)
        await self._session.commit()
        logger.bind(user_id=str(user_id), purpose=purpose).info("EmailVerificationTokenIssued")
        return plain
