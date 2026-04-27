from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse, urlunparse

from loguru import logger as log
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.backend.core.config import settings
from src.backend.database.postgres.models import Base

# --- Connection Configuration ---

connect_args: dict[str, Any] = {
    "prepared_statement_cache_size": 0,
}

db_url = settings.sqlalchemy_database_url

# --- Safety Check: Forbid SQLite ---
if "sqlite" in db_url:
    error_msg = (
        "❌ CRITICAL ERROR: SQLite usage is forbidden in this project configuration. "
        "Please configure PostgreSQL in .env (DATABASE_URL)."
    )
    log.critical(error_msg)
    raise RuntimeError(error_msg)

# Handle SSL mode for asyncpg
if "sslmode" in db_url or settings.db_ssl_require:
    connect_args["ssl"] = "require"
    try:
        parsed = urlparse(db_url)
        if parsed.query:
            db_url = urlunparse(parsed._replace(query=""))
    except Exception as parse_exc:  # noqa: BLE001
        log.warning(f"Database | action=parse_url_failed error={parse_exc}")

pool_settings: dict[str, Any] = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_pre_ping": True,
}

async_engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    **pool_settings,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для работы с БД (для воркеров, скриптов и сервисов).
    Автоматически делает commit при успехе и rollback при ошибке.

    Usage:
        async with get_session_context() as session:
            repo = UsersRepo(session)
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            log.error(f"DatabaseSession | action=commit status=failed error={e}")
            raise
        except Exception as e:
            await session.rollback()
            log.exception(f"DatabaseSession | action=unknown_error status=failed error={e}")
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI (Depends(get_db)).
    Использует тот же механизм с авто-коммитом.
    """
    async with get_session_context() as session:
        yield session


async def create_db_tables() -> None:
    """
    Создает таблицы в БД (используется для Dev режима или тестов).
    В проде лучше использовать Alembic.
    """
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Database | action=create_tables status=success")
    except SQLAlchemyError as db_exc:
        log.critical(f"Database | action=create_tables status=failed error={db_exc}")
        raise


async def run_alembic_migrations() -> None:
    """
    Run Alembic migrations programmatically using Alembic API.
    Temporarily disabled until Alembic is initialized.
    """
    pass


__all__ = ["Base", "get_db", "get_session_context", "create_db_tables", "run_alembic_migrations", "async_engine"]
