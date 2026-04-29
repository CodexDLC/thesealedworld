import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import redis.asyncio as redis
from codex_platform.redis_service import RedisService
from codex_platform.streams.consumer import StreamConsumer
from codex_platform.streams.dispatcher import StreamDispatcher
from codex_platform.streams.processor import StreamProcessor
from codex_platform.streams.producer import StreamProducer
from fastapi import FastAPI

from src.backend.config.settings import settings
from src.backend.core.bus import GameEventProducer
from src.backend.core.database import create_db_tables
from src.backend.core.redis.actor_snapshot_manager import ActorSnapshotManager
from src.backend.core.redis.character_session_events import CharacterSessionEvents
from src.backend.core.redis.character_session_manager import CharacterSessionManager
from src.backend.core.redis.managers import RedisManagers
from src.backend.features.actor_state.events import bind as bind_actor_state_events
from src.backend.features.actor_state.events import router as actor_state_router
from src.backend.features.arena.events import router as arena_router
from src.backend.features.auth.events import router as auth_router
from src.backend.features.chat.events import router as chat_router
from src.backend.features.combat.events import router as combat_router
from src.backend.features.exploration.events import router as exploration_router
from src.backend.features.game_menu.events import router as game_menu_router
from src.backend.features.inventory.events import router as inventory_router
from src.backend.features.scenario.events import router as scenario_router
from src.backend.features.world.events import router as world_router

log = logging.getLogger(__name__)


async def start_event_bus(app: FastAPI) -> None:
    app.state.redis_client = redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    app.state.events = GameEventProducer(StreamProducer(app.state.redis_client, settings.game_stream_name))
    redis_service = RedisService(app.state.redis_client)
    managers = RedisManagers(
        redis=redis_service,
        character_sessions=CharacterSessionManager(redis_service),
        actor_snapshots=ActorSnapshotManager(redis_service),
    )
    app.state.redis = redis_service
    app.state.redis_managers = managers
    app.state.character_sessions = managers.character_sessions
    app.state.character_session_events = CharacterSessionEvents(app.state.events)
    app.state.actor_snapshots = managers.actor_snapshots
    bind_actor_state_events(app)

    dispatcher = StreamDispatcher()
    dispatcher.include_router(auth_router)
    dispatcher.include_router(chat_router)
    dispatcher.include_router(world_router)
    dispatcher.include_router(actor_state_router)
    dispatcher.include_router(combat_router)
    dispatcher.include_router(inventory_router)
    dispatcher.include_router(exploration_router)
    dispatcher.include_router(scenario_router)
    dispatcher.include_router(game_menu_router)
    dispatcher.include_router(arena_router)

    app.state.processor = StreamProcessor(
        storage=StreamConsumer(  # type: ignore[arg-type]
            app.state.redis_client,
            settings.game_stream_name,
            settings.monolith_group,
            settings.worker_name,
        ),
        stream_name=settings.game_stream_name,
        consumer_group_name=settings.monolith_group,
        consumer_name=settings.worker_name,
    )

    app.state.processor.set_callback(dispatcher.process)
    app.state.processor_task = asyncio.create_task(app.state.processor.start())
    log.info("Event bus started: stream=%s group=%s", settings.game_stream_name, settings.monolith_group)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_tables()
    await start_event_bus(app)

    yield

    if hasattr(app.state, "processor_task"):
        app.state.processor_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state.processor_task

    await app.state.redis_client.close()
    log.info("Event bus stopped.")
