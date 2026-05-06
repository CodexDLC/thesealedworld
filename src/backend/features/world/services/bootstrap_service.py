from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.backend.features.world.integrations import WorldDataIntegration
    from src.backend.features.world.services.cache_service import WorldCacheService

log = logging.getLogger(__name__)


class WorldGenerator(Protocol):
    async def run(self, mode: str = "test") -> None: ...


class WorldBootstrapService:
    """Startup coordinator for persistent world data and runtime cache.

    Generation is intentionally optional. Normal app startup should not drop
    schemas, call LLMs, or rewrite the world unless explicitly configured.
    """

    def __init__(
        self,
        data: WorldDataIntegration,
        cache: WorldCacheService,
        generator: WorldGenerator | None = None,
        *,
        auto_generate: bool = False,
        generation_mode: str = "test",
        refresh_static_seed: bool = True,
    ) -> None:
        self.data = data
        self.cache = cache
        self.generator = generator
        self.auto_generate = auto_generate
        self.generation_mode = generation_mode
        self.refresh_static_seed = refresh_static_seed

    async def bootstrap(self) -> int:
        has_world = await self.data.has_world_data()
        if not has_world:
            if self.auto_generate and self.generator is not None:
                log.info("World data missing; running generator mode=%s", self.generation_mode)
                await self.generator.run(self.generation_mode)
            elif self.refresh_static_seed and self.generator is not None:
                log.info("World data missing; loading static world seed")
                await self.generator.run("test")
            else:
                log.warning("World data missing; startup generation is disabled")
                return 0
        elif self.refresh_static_seed and self.generator is not None:
            log.info("World data exists; refreshing static world seed")
            await self.generator.run("test")

        active_nodes = await self.data.count_active_nodes()
        if active_nodes <= 0:
            log.warning("World data exists but no active nodes are available for runtime cache")
            return 0

        return await self.cache.warm_runtime_cache()
