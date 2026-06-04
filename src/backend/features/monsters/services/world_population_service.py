from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.monsters.services.encounter_monster_service import EncounterMonsterService
    from src.backend.infrastructure.world.models import WorldGrid


@dataclass(frozen=True, slots=True)
class MonsterPopulationResult:
    contexts: int
    clans: int


class WorldMonsterPopulationService:
    """Node-tag monster population seeding is no longer part of runtime generation.

    World/rift monster generation now materializes habitat clan pools from
    region/rift configs. Keeping this class as a hard-fail shim prevents old
    node/location tags from silently creating clan identities.
    """

    def __init__(self, encounter_service: EncounterMonsterService) -> None:
        del encounter_service

    async def ensure_population_for_nodes(self, nodes: list[WorldGrid]) -> MonsterPopulationResult:
        del nodes
        raise RuntimeError(
            "WorldMonsterPopulationService was replaced by HabitatClanPoolMaterializationService; "
            "materialize clans from WorldRegion.population_profile instead of node context tags."
        )
