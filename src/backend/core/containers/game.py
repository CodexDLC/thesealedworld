from pathlib import Path

from fastapi import FastAPI
from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.database import get_manual_session_context, get_session_context
from src.backend.core.mongo import get_mongo_provider
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
    HabitatClanPoolMaterializationService,
)
from src.backend.features.monsters.services.habitat_clan_pool_materialization_service import (
    habitat_scope_config_from_population_profile,
)
from src.backend.features.rift.resources.loader import RiftResourceLoader
from src.backend.features.rift.services import RiftCatalogBootstrapService, RiftPopulationBootstrapService
from src.backend.features.scenario.integrations import ScenarioImportIntegration
from src.backend.features.world.integrations import WorldDataIntegration, WorldLocationIntegration
from src.backend.features.world.services import LLMWorldGenerator, WorldBootstrapService, WorldCacheService
from src.backend.infrastructure.rift.repositories import RiftNodePoolRepository, RiftSettingRepository
from src.backend.infrastructure.rift.repositories.catalog_documents import RiftCatalogDocumentRepository
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
            encounter_service = EncounterMonsterService(  # type: ignore
                MonsterGenerationRepository(session),
                factory=ClanFactory(  # type: ignore
                    MonsterClanGenerationBuilder(  # type: ignore
                        repository=MonsterGenerationRepository(session),
                        item_generation=ItemGenerationService(
                            ItemPersistenceIntegration(ItemInstanceRepository(session)),
                        ),
                        generation_ai=generation_ai,
                    ),
                ),
            )
            monster_factory = encounter_service.factory
            habitat_materializer = HabitatClanPoolMaterializationService(  # type: ignore
                repository=MonsterGenerationRepository(session),
                factory=monster_factory,
            )
            active_regions = await data.get_active_regions()
            population_result = await habitat_materializer.ensure_scope_pools(
                [
                    habitat_scope_config_from_population_profile(
                        scope_type="region",
                        scope_id=str(region.id),
                        population_profile=dict(region.population_profile or {}),
                        default_biome=str(region.biome_id or "wasteland"),
                        tier=max(1, int(region.tier_min or 1)),
                        source_meta={"region_archetype": str(region.region_archetype or "")},
                    )
                    for region in active_regions
                    if isinstance(region.population_profile, dict)
                    and region.population_profile.get("habitat")
                    and region.population_profile.get("clan_pool_policy")
                ]
            )
            rift_loader = RiftResourceLoader()
            rift_catalog_result = await RiftCatalogBootstrapService(
                loader=rift_loader,
                setting_repository=RiftSettingRepository(session),
                node_pool_repository=RiftNodePoolRepository(session),
                catalog_document_repository=RiftCatalogDocumentRepository(get_mongo_provider().database()),
            ).sync_fixtures()
            rift_population_result = await RiftPopulationBootstrapService(
                loader=rift_loader,
                materializer=habitat_materializer,
            ).ensure_static_population()
            app.state.world_cache_loaded_count = loaded_count
            app.state.monster_population_contexts = population_result.scopes
            app.state.monster_population_clans = population_result.clans
            app.state.rift_catalog_settings = rift_catalog_result.settings
            app.state.rift_catalog_nodes = rift_catalog_result.nodes
            app.state.rift_population_rifts = rift_population_result.rifts
            app.state.rift_population_family_slots = rift_population_result.family_slots
            app.state.rift_population_clans = rift_population_result.clans
            app.state.rift_population_bindings = rift_population_result.bindings
            logger.bind(location_count=loaded_count).info("WorldBootstrapFinished")
            logger.bind(
                context_count=population_result.scopes,
                clan_count=population_result.clans,
            ).info("MonsterPopulationBootstrapFinished")
            logger.bind(
                setting_count=rift_catalog_result.settings,
                node_count=rift_catalog_result.nodes,
            ).info("RiftCatalogBootstrapFinished")
            logger.bind(
                rift_count=rift_population_result.rifts,
                slot_count=rift_population_result.family_slots,
                clan_count=rift_population_result.clans,
            ).info("RiftPopulationBootstrapFinished")
            await session.commit()
            scheduled = await generation_ai.schedule_pending_task_ids()
            logger.bind(task_count=scheduled).info("GenerationAiBootstrapTasksScheduled")

    async def _bootstrap_anchor_projections(self, app: FastAPI) -> None:
        logger.info("AnchorProjectionsBootstrapStarted")
        item_generation = ItemGenerationService()
        bootstrap = AnchorProjectionBootstrapService(  # type: ignore
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
