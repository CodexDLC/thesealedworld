import redis.asyncio as redis
from codex_platform.redis_service import RedisService
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from fastapi import FastAPI
from loguru import logger as log

from src.backend.config.settings import settings
from src.backend.core.arq import GENERATION_AI_ARQ_QUEUE, SYSTEM_ARQ_QUEUE, ArqService
from src.backend.core.bus import GameEventProducer
from src.backend.features.arena.events import bind as bind_arena_events
from src.backend.features.arena.events import router as arena_router
from src.backend.features.character.events import bind as bind_character_events
from src.backend.features.character.events import router as character_router
from src.backend.features.character.events.publisher import CharacterSessionEvents
from src.backend.features.city_services.events import bind as bind_city_services_events
from src.backend.features.city_services.events import router as city_services_router
from src.backend.features.combat.events import bind as bind_combat_events
from src.backend.features.combat.events import router as combat_router

# Game Config
from src.backend.features.combat.game_config import CombatConfig
from src.backend.features.exploration.game_config import ExplorationConfig
from src.backend.features.inventory.events import bind as bind_inventory_events
from src.backend.features.inventory.events import router as inventory_router
from src.backend.features.items.events import bind as bind_items_events
from src.backend.features.items.events import router as items_router
from src.backend.features.loot.events import bind as bind_loot_events
from src.backend.features.loot.events import router as loot_router
from src.backend.features.monsters.events import bind as bind_monsters_events
from src.backend.features.monsters.events import router as monsters_router
from src.backend.features.scenario.events import bind as bind_scenario_events
from src.backend.features.scenario.events import router as scenario_router
from src.backend.features.scenario.game_config import ScenarioConfig
from src.backend.features.world.events import router as world_router
from src.backend.infrastructure.game_config.manager import GameConfigManager

# Infrastructure Managers
from src.backend.infrastructure.redis.managers import build_redis_managers

_GAME_CONFIGS = (CombatConfig, ExplorationConfig, ScenarioConfig)

EVENT_ROUTER_GROUPS = (
    ("character", character_router),
    ("combat", combat_router),
    ("inventory", inventory_router),
    ("items", items_router),
    ("loot", loot_router),
    ("monsters", monsters_router),
    ("scenario", scenario_router),
    ("arena", arena_router),
    ("city_services", city_services_router),
)


class RedisContainer:
    """Manages Redis connection, managers, and Event Bus."""

    async def bootstrap(self, app: FastAPI) -> None:
        log.info("RedisBootstrapStarted")

        # 1. Redis Client & Service
        app.state.redis_client = redis.from_url(
            settings.effective_redis_url,
            decode_responses=True,
        )
        redis_service = RedisService(app.state.redis_client)

        # 2. Managers
        managers = build_redis_managers(redis_service)

        game_config = GameConfigManager(app.state.redis_client)
        for cfg in _GAME_CONFIGS:
            game_config.register(cfg)
        await game_config.bootstrap()
        app.state.game_config = game_config

        app.state.redis = redis_service
        app.state.combat_arq = ArqService()
        app.state.system_arq = ArqService(queue_name=SYSTEM_ARQ_QUEUE)
        app.state.generation_ai_arq = ArqService(queue_name=GENERATION_AI_ARQ_QUEUE)
        app.state.redis_managers = managers
        app.state.character_sessions = managers.character_sessions
        app.state.actor_commitments = managers.actor_commitments
        app.state.scenario_sessions = managers.scenario_sessions
        app.state.scenario_content = managers.scenario_content
        app.state.world_locations = managers.world_locations

        # 3. Stream Runtimes
        runtimes = self._build_stream_runtimes(app)

        app.state.stream_runtimes = runtimes
        app.state.stream_runtime = runtimes[0]
        app.state.events = GameEventProducer(runtimes[0].producer, maxlen=settings.game_stream_maxlen)
        app.state.character_session_events = CharacterSessionEvents(app.state.events)

        # Bind events to app
        bind_character_events(app)
        bind_combat_events(app)
        bind_arena_events(app)
        bind_inventory_events(app)
        bind_items_events(app)
        bind_loot_events(app)
        bind_monsters_events(app)
        bind_scenario_events(app)
        bind_city_services_events(app)

        for runtime in runtimes:
            await runtime.start()

        log.bind(groups=[runtime.config.consumer_group for runtime in runtimes]).info("RedisStreamRuntimesStarted")
        log.info("RedisBootstrapFinished")

    def _build_stream_runtimes(self, app: FastAPI) -> list[StreamRuntime]:
        if settings.stream_enabled_groups is not None:
            runtime = StreamRuntime(
                redis=app.state.redis_client,
                config=StreamRuntimeConfig(
                    stream_name=settings.game_stream_name,
                    consumer_group=settings.stream_consumer_group,
                    consumer_name=settings.worker_name,
                    enabled_groups=settings.stream_enabled_groups,
                ),
            )
            self._register_all_routers(runtime)
            return [runtime]

        runtimes: list[StreamRuntime] = []
        for group, router in EVENT_ROUTER_GROUPS:
            runtime = StreamRuntime(
                redis=app.state.redis_client,
                config=StreamRuntimeConfig(
                    stream_name=settings.game_stream_name,
                    consumer_group=group,
                    consumer_name=f"{settings.worker_name}_{group}",
                    enabled_groups=[group],
                ),
            )
            runtime.include_router(router)
            runtimes.append(runtime)

        return runtimes

    def _register_all_routers(self, runtime: StreamRuntime) -> None:
        runtime.include_router(world_router)
        runtime.include_router(character_router)
        runtime.include_router(combat_router)
        runtime.include_router(inventory_router)
        runtime.include_router(items_router)
        runtime.include_router(loot_router)
        runtime.include_router(monsters_router)
        runtime.include_router(scenario_router)
        runtime.include_router(arena_router)
        runtime.include_router(city_services_router)
