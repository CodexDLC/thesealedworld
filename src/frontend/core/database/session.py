from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema

from src.frontend.config.settings import settings
from src.frontend.core.database.base import Base

async_engine = create_async_engine(settings.database_url, echo=settings.database_echo, pool_pre_ping=True)
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def load_orm_models() -> None:
    from src.frontend.core.database import model_imports  # noqa: F401


async def create_db_tables() -> None:
    load_orm_models()
    async with async_engine.begin() as conn:
        await conn.execute(CreateSchema("site", if_not_exists=True))
        await conn.run_sync(Base.metadata.create_all)


async def close_db_engine() -> None:
    await async_engine.dispose()
