import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features_site.auth.dto.user import UserCreate
from src.backend.features_site.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreate) -> User:
        db_user = User(
            email=user_in.email,
            hashed_password=user_in.password,
            is_active=True,
            is_superuser=False,
        )
        self.session.add(db_user)
        await self.session.flush()
        await self.session.refresh(db_user)
        return db_user

    async def commit(self) -> None:
        await self.session.commit()
