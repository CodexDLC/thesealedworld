from __future__ import annotations

from typing import Any

import redis.asyncio as redis
from codex_platform.redis_service import RedisService
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.database import load_orm_models
from src.backend.core.repository_factory import RepositoryFactory
from src.backend.infrastructure.redis.managers import build_redis_managers


class ArqWorkerContainer:
    async def bootstrap(self, ctx: dict[str, Any]) -> None:
        load_orm_models()

        redis_client = redis.from_url(settings.effective_redis_url, decode_responses=True)
        redis_service = RedisService(redis_client)
        redis_managers = build_redis_managers(redis_service)

        ctx["worker_container"] = self
        ctx["redis_client_internal"] = redis_client
        ctx["redis_service"] = redis_service
        ctx["redis_managers"] = redis_managers
        ctx["repositories"] = RepositoryFactory()

        ctx["character_sessions"] = redis_managers.character_sessions
        ctx["actor_commitments"] = redis_managers.actor_commitments
        ctx["scenario_sessions"] = redis_managers.scenario_sessions
        ctx["scenario_content"] = redis_managers.scenario_content
        ctx["world_locations"] = redis_managers.world_locations

        logger.info("ARQ worker container bootstrap finished")

    async def shutdown(self, ctx: dict[str, Any]) -> None:
        client = ctx.get("redis_client_internal")
        if client is not None:
            await client.aclose()
            logger.info("ARQ worker Redis client closed")
