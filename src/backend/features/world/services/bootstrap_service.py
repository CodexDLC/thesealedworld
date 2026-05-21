from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from loguru import logger as log

if TYPE_CHECKING:
    from src.backend.features.world.integrations import WorldDataIntegration
    from src.backend.features.world.services.cache_service import WorldCacheService


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
                log.bind(mode=self.generation_mode).info("WorldGeneratorStarted")
                await self.generator.run(self.generation_mode)
            elif self.refresh_static_seed and self.generator is not None:
                log.info("WorldStaticSeedLoading")
                await self.generator.run("test")
            else:
                log.warning("WorldStartupGenerationDisabled")
                return 0
        elif self.refresh_static_seed and self.generator is not None:
            log.info("WorldStaticSeedRefreshing")
            await self.generator.run("test")

        active_nodes = await self.data.count_active_nodes()
        if active_nodes <= 0:
            log.warning("WorldRuntimeCacheWarmupSkipped")
            return 0

        return await self.cache.warm_runtime_cache()
