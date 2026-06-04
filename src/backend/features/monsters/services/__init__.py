from __future__ import annotations

from src.backend.infrastructure.monsters.managers import AnchorProjectionSnapshotCache

__all__ = [
    "AnchorProjectionBootstrapService",
    "AnchorProjectionSnapshotCache",
    "EncounterMonsterService",
    "GeneratedMonsterViewService",
    "HabitatClanPoolMaterializationResult",
    "HabitatClanPoolMaterializationService",
    "HabitatScopeConfig",
    "MonsterGearScoreService",
    "MonsterGroupService",
]


def __getattr__(name: str) -> object:
    if name == "AnchorProjectionBootstrapService":
        from src.backend.features.monsters.services.anchor_projection_bootstrap import AnchorProjectionBootstrapService

        return AnchorProjectionBootstrapService
    if name == "EncounterMonsterService":
        from src.backend.features.monsters.services.encounter_monster_service import EncounterMonsterService

        return EncounterMonsterService
    if name == "GeneratedMonsterViewService":
        from src.backend.features.monsters.services.generated_view_service import GeneratedMonsterViewService

        return GeneratedMonsterViewService
    if name in {"HabitatClanPoolMaterializationResult", "HabitatClanPoolMaterializationService", "HabitatScopeConfig"}:
        from src.backend.features.monsters.services.habitat_clan_pool_materialization_service import (
            HabitatClanPoolMaterializationResult,
            HabitatClanPoolMaterializationService,
            HabitatScopeConfig,
        )

        return {
            "HabitatClanPoolMaterializationResult": HabitatClanPoolMaterializationResult,
            "HabitatClanPoolMaterializationService": HabitatClanPoolMaterializationService,
            "HabitatScopeConfig": HabitatScopeConfig,
        }[name]
    if name == "MonsterGearScoreService":
        from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService

        return MonsterGearScoreService
    if name == "MonsterGroupService":
        from src.backend.features.monsters.services.monster_group_service import MonsterGroupService

        return MonsterGroupService
    raise AttributeError(name)
