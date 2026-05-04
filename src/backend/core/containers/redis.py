import logging

import redis.asyncio as redis
from codex_platform.redis_service import RedisService
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from fastapi import FastAPI

from src.backend.config.settings import settings
from src.backend.core.bus import GameEventProducer

# Event Routers & Publishers
from src.backend.features.actor_state.events import bind as bind_actor_state_events
from src.backend.features.actor_state.events import router as actor_state_router
from src.backend.features.actor_state.events.publisher import CharacterSessionEvents
from src.backend.features.arena.events import bind as bind_arena_events
from src.backend.features.arena.events import router as arena_router
from src.backend.features.character.events import bind as bind_character_events
from src.backend.features.character.events import router as character_router
from src.backend.features.combat.events import bind as bind_combat_events
from src.backend.features.combat.events import router as combat_router
from src.backend.features.exploration.events import router as exploration_router
from src.backend.features.inventory.events import router as inventory_router
from src.backend.features.items.events import bind as bind_items_events
from src.backend.features.items.events import router as items_router
from src.backend.features.scenario.events import bind as bind_scenario_events
from src.backend.features.scenario.events import router as scenario_router
from src.backend.features.world.events import router as world_router
from src.backend.features_realtime.chat.events import router as chat_router
from src.backend.features_site.auth.events import router as auth_router

# Infrastructure Managers
from src.backend.infrastructure.actor_state import ActorSnapshotManager, CharacterSessionManager
from src.backend.infrastructure.redis.managers import RedisManagers
from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
from src.backend.infrastructure.world import WorldLocationStore

log = logging.getLogger(__name__)


class RedisContainer:
    """Manages Redis connection, managers, and Event Bus."""

    async def bootstrap(self, app: FastAPI) -> None:
        log.info("Bootstrapping Redis & Event Bus...")

        # 1. Redis Client & Service
        app.state.redis_client = redis.from_url(
            settings.effective_redis_url,
            decode_responses=True,
        )
        redis_service = RedisService(app.state.redis_client)

        # 2. Managers
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

        # 3. Stream Runtime
        runtime = StreamRuntime(
            redis=app.state.redis_client,
            config=StreamRuntimeConfig(
                stream_name=settings.game_stream_name,
                consumer_group=settings.stream_consumer_group,
                consumer_name=settings.worker_name,
                enabled_groups=settings.stream_enabled_groups,
            ),
        )

        self._register_routers(runtime)

        app.state.stream_runtime = runtime
        app.state.events = GameEventProducer(runtime.producer, maxlen=settings.game_stream_maxlen)
        app.state.character_session_events = CharacterSessionEvents(app.state.events)

        # Bind events to app
        bind_actor_state_events(app)
        bind_character_events(app)
        bind_combat_events(app)
        bind_arena_events(app)
        bind_items_events(app)
        bind_scenario_events(app)

        await runtime.start()
        log.info("Redis bootstrap finished")

    def _register_routers(self, runtime: StreamRuntime) -> None:
        runtime.include_router(auth_router)
        runtime.include_router(chat_router)
        runtime.include_router(world_router)
        runtime.include_router(actor_state_router)
        runtime.include_router(character_router)
        runtime.include_router(combat_router)
        runtime.include_router(inventory_router)
        runtime.include_router(items_router)
        runtime.include_router(exploration_router)
        runtime.include_router(scenario_router)
        runtime.include_router(arena_router)
