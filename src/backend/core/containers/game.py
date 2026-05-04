from pathlib import Path

from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.database import get_session_context

# Feature Services
from src.backend.features.world.services import LLMWorldGenerator, WorldBootstrapService, WorldCacheService
from src.backend.infrastructure.scenario.repositories import ScenarioRepository
from src.backend.infrastructure.world.repositories import WorldRepository


class GameFeatureContainer:
    """Manages game-specific features like World and Scenarios."""

    async def bootstrap(self, app: FastAPI) -> None:
        logger.info("Bootstrapping Game Features...")
        await self.bootstrap_scenarios(app)
        await self._bootstrap_world(app)
        logger.info("Game Features bootstrap finished")

    async def _bootstrap_world(self, app: FastAPI) -> None:
        logger.info("Bootstrapping World feature...")
        async with get_session_context() as session:
            repository = WorldRepository(session)
            # world_locations were initialized in InfrastructureContainer
            cache = WorldCacheService(repository=repository, locations=app.state.world_locations)
            generator = LLMWorldGenerator(repository, app.state.ai)

            bootstrap = WorldBootstrapService(
                repository=repository,
                cache=cache,
                generator=generator,
                auto_generate=settings.world_auto_generate,
                generation_mode=settings.world_generation_mode,
            )
            loaded_count = await bootstrap.bootstrap()
            app.state.world_cache_loaded_count = loaded_count
            logger.info(f"World bootstrap: {loaded_count} locations loaded")

    async def bootstrap_scenarios(self, app: FastAPI) -> None:
        logger.info("Bootstrapping Scenarios feature...")
        from src.backend.features.scenario.loaders.scenario_loader import ScenarioLoader
        from src.backend.features.scenario.services.content_service import ScenarioContentService

        # Relative path to scenarios JSON
        scenario_path = (
            Path(__file__).resolve().parents[2] / "features" / "scenario" / "resources" / "json" / "awakening_rift"
        )
        if not scenario_path.exists():
            logger.warning(f"Scenario fixture is missing: path={scenario_path}")
            return

        async with get_session_context() as session:
            repository = ScenarioRepository(session)
            # redis service was initialized in InfrastructureContainer
            content = ScenarioContentService(repository, app.state.redis)
            loader = ScenarioLoader(session, content=content)
            quest_key = await loader.load_from_file(scenario_path)
            app.state.scenario_bootstrap_quest_key = quest_key
            logger.info(f"Scenarios bootstrap: quest_key={quest_key} loaded")
