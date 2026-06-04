from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.session import get_db
from src.backend.core.mongo import get_mongo_provider
from src.backend.features.combat.integrations import CombatSessionIntegration, CombatSystemIntegrator
from src.backend.features.combat.orchestrators import CombatCreationOrchestrator
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService
from src.backend.features.combat.services.loot_preorder_service import CombatLootPreorderService
from src.backend.features.generation_ai.bootstrap import build_generation_ai_registry
from src.backend.features.generation_ai.repositories import AIGenerationTaskRepository
from src.backend.features.generation_ai.services import GenerationAIService
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services import ItemGenerationService
from src.backend.features.loot.integrations import LootOrderStreamClient
from src.backend.features.monsters.integrations import (
    MonsterActorCommitmentIntegration,
    MonsterLocationContextIntegration,
)
from src.backend.features.monsters.repositories import MonsterGenerationRepository
from src.backend.features.monsters.runtime import ClanFactory, MonsterClanGenerationBuilder
from src.backend.features.monsters.services import MonsterGroupService
from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.features.rift.services import RiftDevService, RiftEncounterService, RiftEntryService, RiftPlayerService
from src.backend.infrastructure.monsters.managers import MonsterGroupCacheManager
from src.backend.infrastructure.rift.managers import (
    RiftInstanceStore,
    RiftPortalStore,
    RiftPresenceStore,
    RiftRestoreLock,
    RiftRunSessionStore,
)
from src.backend.infrastructure.rift.repositories import RiftMembershipRepository
from src.backend.infrastructure.rift.repositories.snapshots import RiftRuntimeSnapshotRepository


def _build_rift_runtime_integration(
    request: Request,
    db_session: AsyncSession | None = None,
) -> RiftRuntimeIntegration:
    redis = request.app.state.redis
    return RiftRuntimeIntegration(
        instance_store=RiftInstanceStore(redis),
        session_store=RiftRunSessionStore(redis),
        presence_store=RiftPresenceStore(redis),
        portal_store=RiftPortalStore(redis),
        membership_repository=RiftMembershipRepository(db_session) if db_session is not None else None,
        snapshot_repository=RiftRuntimeSnapshotRepository(get_mongo_provider().database())
        if db_session is not None
        else None,
        restore_lock=RiftRestoreLock(redis),
    )


def get_rift_runtime_integration(request: Request) -> RiftRuntimeIntegration:
    return _build_rift_runtime_integration(request)


def get_rift_dev_service(
    request: Request,
    runtime: Annotated[RiftRuntimeIntegration, Depends(get_rift_runtime_integration)],
) -> RiftDevService:
    return RiftDevService(runtime=runtime, game_config=getattr(request.app.state, "game_config", None))


def get_rift_entry_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> RiftEntryService:
    runtime = _build_rift_runtime_integration(request, db_session)
    return RiftEntryService(
        runtime=runtime,
        character_sessions=request.app.state.character_sessions,
        rift_population_bindings=getattr(request.app.state, "rift_population_bindings", {}),
    )


def get_rift_player_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> RiftPlayerService:
    runtime = _build_rift_runtime_integration(request, db_session)
    return RiftPlayerService(
        runtime=runtime,
        character_sessions=request.app.state.character_sessions,
        game_config=getattr(request.app.state, "game_config", None),
    )


def get_rift_game_player_service(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db)],
) -> RiftPlayerService:
    runtime = _build_rift_runtime_integration(request, db_session)
    return RiftPlayerService(
        runtime=runtime,
        character_sessions=request.app.state.character_sessions,
        encounters=_rift_encounter_service(request=request, db_session=db_session, runtime=runtime),
        game_config=getattr(request.app.state, "game_config", None),
    )


def _rift_encounter_service(
    *,
    request: Request,
    db_session: AsyncSession,
    runtime: RiftRuntimeIntegration,
) -> RiftEncounterService:
    monster_repository = MonsterGenerationRepository(db_session)
    item_generation = ItemGenerationService(
        ItemPersistenceIntegration(ItemInstanceRepository(db_session)),
    )
    generation_ai = GenerationAIService(
        repository=AIGenerationTaskRepository(db_session),
        registry=build_generation_ai_registry(session=db_session),
        arq=getattr(request.app.state, "generation_ai_arq", None),
        auto_schedule=False,
    )
    monster_groups = MonsterGroupService(  # type: ignore
        repository=monster_repository,
        location_context=MonsterLocationContextIntegration(request.app.state.world_locations),
        actor_commitments=MonsterActorCommitmentIntegration(request.app.state.actor_commitments),
        group_cache=MonsterGroupCacheManager(request.app.state.redis),
        factory=ClanFactory(  # type: ignore
            MonsterClanGenerationBuilder(  # type: ignore
                repository=monster_repository,
                item_generation=item_generation,
                generation_ai=generation_ai,
            ),
        ),
    )
    combat_creator = CombatCreationOrchestrator(
        lifecycle=CombatLifecycleService(store=CombatSessionIntegration.from_redis(request.app.state.redis)),
        integrator=CombatSystemIntegrator(
            actor_commitments=request.app.state.actor_commitments,
            character_sessions=request.app.state.character_sessions,
            events=request.app.state.events,
            redis=request.app.state.redis,
        ),
        loot_preorder=CombatLootPreorderService(LootOrderStreamClient(request.app.state.events)),
    )
    return RiftEncounterService(
        monster_groups=monster_groups,
        combat_creator=combat_creator,
        runtime=runtime,
        character_sessions=request.app.state.character_sessions,
    )
