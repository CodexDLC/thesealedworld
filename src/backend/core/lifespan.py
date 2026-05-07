from contextlib import asynccontextmanager

import redis.asyncio as redis
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.bus import GameEventProducer
from src.backend.core.containers import AIContainer, DatabaseContainer, GameFeatureContainer, RedisContainer
from src.backend.features.arena.events import router as arena_router
from src.backend.features.character.events import router as character_router
from src.backend.features.combat.events import router as combat_router
from src.backend.features.exploration.events import router as exploration_router
from src.backend.features.inventory.events import router as inventory_router
from src.backend.features.items.events import router as items_router
from src.backend.features.scenario.events import router as scenario_router
from src.backend.features.world.events import router as world_router
from src.backend.features_site.auth.events import router as auth_router

EVENT_ROUTERS = (
    auth_router,
    world_router,
    character_router,
    combat_router,
    inventory_router,
    items_router,
    exploration_router,
    scenario_router,
    arena_router,
)


async def start_event_bus(app: FastAPI) -> None:
    """Compatibility helper for tests and scripts that start only Redis Streams."""

    if not hasattr(app.state, "redis_client"):
        app.state.redis_client = redis.from_url(
            settings.effective_redis_url,
            decode_responses=True,
        )

    runtime = StreamRuntime(
        redis=app.state.redis_client,
        config=StreamRuntimeConfig(
            stream_name=settings.game_stream_name,
            consumer_group=settings.stream_consumer_group,
            consumer_name=settings.worker_name,
            enabled_groups=settings.stream_enabled_groups,
        ),
    )

    for router in EVENT_ROUTERS:
        runtime.include_router(router)

    app.state.stream_runtime = runtime
    app.state.events = GameEventProducer(runtime.producer, maxlen=settings.game_stream_maxlen)

    await runtime.start()


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
        if hasattr(app.state, "stream_runtimes"):
            for runtime in app.state.stream_runtimes:
                await runtime.stop()
        elif hasattr(app.state, "stream_runtime"):
            await app.state.stream_runtime.stop()

        if hasattr(app.state, "system_arq"):
            await app.state.system_arq.close()

        if hasattr(app.state, "redis_client"):
            await app.state.redis_client.close()

    except Exception:
        logger.critical("Backend shutdown failed", exc_info=True)
        raise
    logger.info("Backend shutdown finished")
