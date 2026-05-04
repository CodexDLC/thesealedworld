from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.backend.core.containers import AIContainer, DatabaseContainer, GameFeatureContainer, RedisContainer


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend startup started")

    # Initialize containers
    db = DatabaseContainer()
    rd = RedisContainer()
    ai = AIContainer()
    game = GameFeatureContainer()

    try:
        # 1. Database
        await db.bootstrap(app)

        # 2. Redis & Event Bus
        await rd.bootstrap(app)

        # 3. AI Services
        await ai.bootstrap(app)

        # 4. Game Features
        await game.bootstrap(app)

    except Exception:
        logger.critical("Backend startup failed", exc_info=True)
        raise

    logger.info("Backend startup finished")

    yield

    logger.info("Backend shutdown started")
    try:
        if hasattr(app.state, "stream_runtime"):
            await app.state.stream_runtime.stop()

        if hasattr(app.state, "redis_client"):
            await app.state.redis_client.close()

    except Exception:
        logger.critical("Backend shutdown failed", exc_info=True)
        raise
    logger.info("Backend shutdown finished")
