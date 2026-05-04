import logging

from fastapi import FastAPI

from src.backend.core.database import create_db_tables

log = logging.getLogger(__name__)


class DatabaseContainer:
    """Manages Database connection and schema initialization."""

    async def bootstrap(self, app: FastAPI) -> None:
        log.info("Bootstrapping Database...")
        await create_db_tables()
        log.info("Database bootstrap finished")
