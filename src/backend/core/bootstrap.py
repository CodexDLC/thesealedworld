from fastapi import FastAPI
from loguru import logger

from src.backend.core.containers import DatabaseContainer, GameFeatureContainer, RedisContainer


async def bootstrap_scenarios() -> None:
    """Standalone bootstrap for scenarios (used by manage.py)."""
    logger.info("Starting standalone scenario bootstrap...")
    app = FastAPI()

    # 1. Database (for session context)
    db = DatabaseContainer()
    await db.bootstrap(app)

    # 2. Redis (for cache warming)
    rd = RedisContainer()
    await rd.bootstrap(app)

    # 3. Game Features
    game = GameFeatureContainer()
    await game.bootstrap_scenarios(app)

    logger.info("Standalone scenario bootstrap finished")
