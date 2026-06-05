import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.features.auth.dto.user import UserCreate
from src.frontend.features.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return int(result.scalar_one() or 0)

    async def count_matching(self, query: str = "") -> int:
        stmt = select(func.count()).select_from(User)
        if query:
            stmt = stmt.where(User.email.ilike(f"%{query}%"))
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_page(self, *, limit: int, offset: int, query: str = "") -> list[User]:
        stmt = select(User)
        if query:
            stmt = stmt.where(User.email.ilike(f"%{query}%"))
        result = await self.session.execute(stmt.order_by(User.created_at.desc()).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def create(
        self,
        user_in: UserCreate,
        *,
        referral_code: str,
        referred_by_id: uuid.UUID | None = None,
    ) -> User:
        db_user = User(
            email=user_in.email,
            hashed_password=user_in.password,
            is_active=True,
            is_superuser=False,
            referral_code=referral_code,
            referred_by_id=referred_by_id,
        )
        self.session.add(db_user)
        await self.session.flush()
        await self.session.refresh(db_user)
        return db_user

    async def get_by_referral_code(self, code: str) -> User | None:
        result = await self.session.execute(select(User).where(User.referral_code == code))
        return result.scalar_one_or_none()

    async def get_referral_stats(self, user_id: uuid.UUID) -> dict[str, Any]:
        invited = await self.session.execute(
            select(func.count()).select_from(User).where(User.referred_by_id == user_id)
        )
        return {
            "invited": int(invited.scalar_one() or 0),
            "active": 0,  # Activation logic lands with email verification (PR-4).
            "bonus": 0,
        }

    async def update_tester_status(
        self,
        user_id: uuid.UUID,
        status: str,
        *,
        approved_at: datetime | None = None,
    ) -> None:
        values: dict = {"tester_status": status}
        if approved_at is not None:
            values["tester_approved_at"] = approved_at
        stmt = update(User).where(User.id == user_id).values(**values)
        await self.session.execute(stmt)

    async def get_pending_testers(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.tester_status == "pending"))
        return result.scalars().all()

    async def get_approved_testers(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.tester_status == "approved"))
        return result.scalars().all()

    async def commit(self) -> None:
        await self.session.commit()
