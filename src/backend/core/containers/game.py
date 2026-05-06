from pathlib import Path

from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.database import get_session_context

# Feature Services
from src.backend.features.scenario.integrations import ScenarioImportIntegration
from src.backend.features.world.integrations import WorldDataIntegration, WorldLocationIntegration
from src.backend.features.world.services import LLMWorldGenerator, WorldBootstrapService, WorldCacheService
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
            data = WorldDataIntegration(repository)
            locations = WorldLocationIntegration(app.state.world_locations)
            # world_locations were initialized in InfrastructureContainer
            cache = WorldCacheService(data=data, locations=locations)
            generator = LLMWorldGenerator(data, app.state.ai)

            bootstrap = WorldBootstrapService(
                data=data,
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

        # Relative path to scenarios JSON
        scenario_path = (
            Path(__file__).resolve().parents[2] / "features" / "scenario" / "resources" / "json" / "awakening_rift"
        )
        if not scenario_path.exists():
            logger.warning(f"Scenario fixture is missing: path={scenario_path}")
            return

        async with get_session_context() as session:
            importer = ScenarioImportIntegration.from_session(session, cache=app.state.scenario_content)
            loader = ScenarioLoader(importer)
            quest_key = await loader.load_from_file(scenario_path)
            app.state.scenario_bootstrap_quest_key = quest_key
            logger.info(f"Scenarios bootstrap: quest_key={quest_key} loaded")
