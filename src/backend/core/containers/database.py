from fastapi import FastAPI
from loguru import logger as log

from src.backend.core.database import create_db_tables


class DatabaseContainer:
    """Manages Database connection and schema initialization."""

    async def bootstrap(self, app: FastAPI) -> None:
        log.info("DatabaseBootstrapStarted")
        await create_db_tables()
        log.info("DatabaseBootstrapFinished")
