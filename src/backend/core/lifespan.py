import logging
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as redis
from codex_platform.redis_service import RedisService
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from fastapi import FastAPI

from src.backend.config.settings import settings
from src.backend.core.bus import GameEventProducer
from src.backend.core.database import create_db_tables
from src.backend.features.actor_state.events import bind as bind_actor_state_events
from src.backend.features.actor_state.events import router as actor_state_router
from src.backend.features.arena.events import router as arena_router
from src.backend.features.auth.events import router as auth_router
from src.backend.features.chat.events import router as chat_router
from src.backend.features.combat.events import router as combat_router
from src.backend.features.exploration.events import router as exploration_router
from src.backend.features.game_menu.events import router as game_menu_router
from src.backend.features.inventory.events import router as inventory_router
from src.backend.features.scenario.events import bind as bind_scenario_events
from src.backend.features.scenario.events import router as scenario_router
from src.backend.features.world.events import router as world_router
from src.backend.features.world.services import WorldBootstrapService, WorldCacheService
from src.backend.infrastructure.db.scenario.repositories import ScenarioRepository
from src.backend.infrastructure.db.world.repositories import WorldRepository
from src.backend.infrastructure.redis.actor_snapshot_manager import ActorSnapshotManager
from src.backend.infrastructure.redis.character_session_events import CharacterSessionEvents
from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager
from src.backend.infrastructure.redis.managers import RedisManagers
from src.backend.infrastructure.redis.scenario import ScenarioSessionManager
from src.backend.infrastructure.redis.world import WorldLocationStore

log = logging.getLogger(__name__)


async def start_event_bus(app: FastAPI) -> None:
    app.state.redis_client = redis.from_url(
        settings.effective_redis_url,
        decode_responses=True,
    )

    redis_service = RedisService(app.state.redis_client)
    managers = RedisManagers(
        redis=redis_service,
        character_sessions=CharacterSessionManager(redis_service),
        actor_snapshots=ActorSnapshotManager(redis_service),
        scenario_sessions=ScenarioSessionManager(redis_service),
        world_locations=WorldLocationStore(redis_service),
    )
    app.state.redis = redis_service
    app.state.redis_managers = managers
    app.state.character_sessions = managers.character_sessions
    app.state.actor_snapshots = managers.actor_snapshots
    app.state.scenario_sessions = managers.scenario_sessions
    app.state.world_locations = managers.world_locations

    runtime = StreamRuntime(
        redis=app.state.redis_client,
        config=StreamRuntimeConfig(
            stream_name=settings.game_stream_name,
            consumer_group=settings.stream_consumer_group,
            consumer_name=settings.worker_name,
            enabled_groups=settings.stream_enabled_groups,
        ),
    )

    runtime.include_router(auth_router)
    runtime.include_router(chat_router)
    runtime.include_router(world_router)
    runtime.include_router(actor_state_router)
    runtime.include_router(combat_router)
    runtime.include_router(inventory_router)
    runtime.include_router(exploration_router)
    runtime.include_router(scenario_router)
    runtime.include_router(game_menu_router)
    runtime.include_router(arena_router)

    app.state.stream_runtime = runtime
    app.state.events = GameEventProducer(runtime.producer)
    app.state.character_session_events = CharacterSessionEvents(app.state.events)
    bind_actor_state_events(app)
    bind_scenario_events(app)

    await runtime.start()
    log.info("Event bus started: stream=%s group=%s", settings.game_stream_name, settings.stream_consumer_group)


async def bootstrap_world(app: FastAPI) -> None:
    from src.backend.core.database import get_session_context

    async with get_session_context() as session:
        repository = WorldRepository(session)
        cache = WorldCacheService(repository=repository, locations=app.state.world_locations)
        bootstrap = WorldBootstrapService(
            repository=repository,
            cache=cache,
            auto_generate=settings.world_auto_generate,
            generation_mode=settings.world_generation_mode,
        )
        loaded_count = await bootstrap.bootstrap()
        app.state.world_cache_loaded_count = loaded_count


async def bootstrap_scenarios(app: FastAPI | None = None) -> None:
    from src.backend.core.database import get_session_context
    from src.backend.features.scenario.loaders.scenario_loader import ScenarioLoader
    from src.backend.features.scenario.services.content_service import ScenarioContentService

    scenario_path = (
        Path(__file__).resolve().parents[1] / "features" / "scenario" / "resources" / "json" / "awakening_rift"
    )
    if not scenario_path.exists():
        log.warning("Scenario fixture is missing: path=%s", scenario_path)
        return

    async with get_session_context() as session:
        repository = ScenarioRepository(session)

        # Handle Redis service for both app-bound and standalone bootstrap
        temp_client = None
        if app:
            redis_service = app.state.redis
        else:
            import redis.asyncio as aioredis
            from codex_platform.redis_service import RedisService

            temp_client = aioredis.from_url(settings.effective_redis_url, decode_responses=True)
            redis_service = RedisService(temp_client)

        content = ScenarioContentService(repository, redis_service)
        loader = ScenarioLoader(session, content=content)
        quest_key = await loader.load_from_file(scenario_path)

        if app:
            app.state.scenario_bootstrap_quest_key = quest_key

        if temp_client:
            await temp_client.close()

        log.info("Scenario fixture loaded: quest_key=%s", quest_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_tables()
    await start_event_bus(app)
    await bootstrap_scenarios(app)
    await bootstrap_world(app)

    yield

    if hasattr(app.state, "stream_runtime"):
        await app.state.stream_runtime.stop()

    await app.state.redis_client.close()
    log.info("Event bus stopped.")
