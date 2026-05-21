from pathlib import Path

from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.database import get_manual_session_context, get_session_context
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService

# Feature Services
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services import ItemGenerationService
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.runtime import ClanFactory, MonsterClanGenerationBuilder
from src.backend.features.monsters.services import (
    AnchorProjectionBootstrapService,
    EncounterMonsterService,
    WorldMonsterPopulationService,
)
from src.backend.features.scenario.integrations import ScenarioImportIntegration
from src.backend.features.world.integrations import WorldDataIntegration, WorldLocationIntegration
from src.backend.features.world.services import LLMWorldGenerator, WorldBootstrapService, WorldCacheService
from src.backend.infrastructure.world.repositories import WorldRepository


class GameFeatureContainer:
    """Manages game-specific features like World and Scenarios."""

    async def bootstrap(self, app: FastAPI) -> None:
        logger.info("GameFeaturesBootstrapStarted")
        await self.bootstrap_scenarios(app)
        await self._bootstrap_world(app)
        await self._bootstrap_anchor_projections(app)
        logger.info("GameFeaturesBootstrapFinished")

    async def _bootstrap_world(self, app: FastAPI) -> None:
        logger.info("WorldFeatureBootstrapStarted")
        async with get_manual_session_context() as session:
            repository = WorldRepository(session)
            data = WorldDataIntegration(repository)
            locations = WorldLocationIntegration(app.state.world_locations)
            # world_locations were initialized in InfrastructureContainer
            cache = WorldCacheService(data=data, locations=locations)
            generation_ai = GenerationAIService(
                repository=AIGenerationTaskRepository(session),
                registry=build_generation_ai_registry(session=session),
                arq=getattr(app.state, "generation_ai_arq", None),
                auto_schedule=False,
            )
            generator = LLMWorldGenerator(data, generation_ai=generation_ai)

            bootstrap = WorldBootstrapService(
                data=data,
                cache=cache,
                generator=generator,
                auto_generate=settings.world_auto_generate,
                generation_mode=settings.world_generation_mode,
            )
            loaded_count = await bootstrap.bootstrap()
            monster_population = WorldMonsterPopulationService(
                EncounterMonsterService(
                    MonsterGenerationRepository(session),
                    factory=ClanFactory(
                        MonsterClanGenerationBuilder(
                            repository=MonsterGenerationRepository(session),
                            item_generation=ItemGenerationService(
                                ItemPersistenceIntegration(ItemInstanceRepository(session)),
                            ),
                            generation_ai=generation_ai,
                        ),
                    ),
                )
            )
            population_result = await monster_population.ensure_population_for_nodes(await data.get_active_nodes())
            app.state.world_cache_loaded_count = loaded_count
            app.state.monster_population_contexts = population_result.contexts
            app.state.monster_population_clans = population_result.clans
            logger.bind(location_count=loaded_count).info("WorldBootstrapFinished")
            logger.bind(
                context_count=population_result.contexts,
                clan_count=population_result.clans,
            ).info("MonsterPopulationBootstrapFinished")
            await session.commit()
            scheduled = await generation_ai.schedule_pending_task_ids()
            logger.bind(task_count=scheduled).info("GenerationAiBootstrapTasksScheduled")

    async def _bootstrap_anchor_projections(self, app: FastAPI) -> None:
        logger.info("AnchorProjectionsBootstrapStarted")
        item_generation = ItemGenerationService()
        bootstrap = AnchorProjectionBootstrapService(
            item_generation=item_generation,
            redis=app.state.redis,
        )
        result = await bootstrap.bootstrap()
        app.state.anchor_projection_bootstrap = result
        logger.bind(
            clan_id=result["clan_id"],
            member_count=result["members"],
            redis_cached=result["redis_cached"],
        ).info("AnchorProjectionsBootstrapFinished")

    async def bootstrap_scenarios(self, app: FastAPI) -> None:
        logger.info("ScenariosFeatureBootstrapStarted")
        from src.backend.features.scenario.loaders.scenario_loader import ScenarioLoader

        scenario_root = Path(__file__).resolve().parents[2] / "features" / "scenario" / "resources" / "json"
        if not scenario_root.exists():
            logger.bind(path=str(scenario_root)).warning("ScenarioFixturesMissing")
            return

        async with get_session_context() as session:
            importer = ScenarioImportIntegration.from_session(session, cache=app.state.scenario_content)
            loader = ScenarioLoader(importer)
            loaded_quest_keys: list[str] = []
            for scenario_path in sorted(path for path in scenario_root.iterdir() if path.is_dir()):
                quest_key = await loader.load_from_file(scenario_path)
                loaded_quest_keys.append(quest_key)
            app.state.scenario_bootstrap_quest_key = "awakening_rift"
            app.state.scenario_bootstrap_quest_keys = loaded_quest_keys
            logger.bind(quest_keys=loaded_quest_keys).info("ScenariosBootstrapFinished")
