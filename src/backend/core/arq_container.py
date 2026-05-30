from __future__ import annotations

from typing import Any

import redis.asyncio as redis
from codex_platform.redis_service import RedisService
from codex_platform.streams.producer import StreamProducer
from loguru import logger

from src.backend.config.settings import apply_runtime_environment_overrides, settings
from src.backend.core.bus import GameEventProducer
from src.backend.core.database import load_orm_models
from src.backend.core.game_config import CoreConfig
from src.backend.core.repository_factory import RepositoryFactory
from src.backend.features.combat.ai_config import CombatAiConfig
from src.backend.features.combat.game_config import CombatConfig
from src.backend.features.expedition.game_config import ExpeditionConfig
from src.backend.features.exploration.game_config import ExplorationConfig
from src.backend.features.loot.game_config import LootConfig
from src.backend.features.rift.game_config import RiftConfig
from src.backend.features.scenario.game_config import ScenarioConfig
from src.backend.infrastructure.game_config.manager import GameConfigManager
from src.backend.infrastructure.redis.managers import build_redis_managers

_GAME_CONFIGS = (
    CoreConfig,
    CombatConfig,
    CombatAiConfig,
    ExpeditionConfig,
    ExplorationConfig,
    LootConfig,
    ScenarioConfig,
    RiftConfig,
)


class ArqWorkerContainer:
    async def bootstrap(self, ctx: dict[str, Any]) -> None:
        apply_runtime_environment_overrides()
        load_orm_models()

        redis_client = redis.from_url(settings.effective_redis_url, decode_responses=True)
        redis_service = RedisService(redis_client)

        # GameConfigManager must be built BEFORE redis_managers so scenario
        # session TTL can be threaded into ScenarioSessionManager.
        game_config = GameConfigManager(redis_client)
        for cfg in _GAME_CONFIGS:
            game_config.register(cfg)
        await game_config.bootstrap()

        redis_managers = build_redis_managers(redis_service, game_config)

        ctx["worker_container"] = self
        ctx["redis_client_internal"] = redis_client
        ctx["redis_service"] = redis_service
        ctx["redis_managers"] = redis_managers
        ctx["game_config"] = game_config
        ctx["events"] = GameEventProducer(
            StreamProducer(redis_client, settings.game_stream_name),
            maxlen=settings.game_stream_maxlen,
        )
        ctx["repositories"] = RepositoryFactory()

        ctx["character_sessions"] = redis_managers.character_sessions
        ctx["actor_commitments"] = redis_managers.actor_commitments
        ctx["scenario_sessions"] = redis_managers.scenario_sessions
        ctx["scenario_content"] = redis_managers.scenario_content
        ctx["world_locations"] = redis_managers.world_locations
        ctx["expeditions"] = redis_managers.expeditions

        logger.info("ArqWorkerContainerBootstrapFinished")

    async def shutdown(self, ctx: dict[str, Any]) -> None:
        client = ctx.get("redis_client_internal")
        if client is not None:
            await client.aclose()
            logger.info("ArqWorkerRedisClientClosed")
