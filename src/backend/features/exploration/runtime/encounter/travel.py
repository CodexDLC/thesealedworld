from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.exploration.runtime.encounter.discoveries import (
    MonsterDiscoveryBuilder,
    build_merchant_placeholder,
    build_resource_placeholder,
    build_rift_placeholder,
)

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
    from src.backend.features.exploration.runtime.encounter.policy import EncounterPolicy
    from src.shared.schemas.exploration import EncounterDTO


class TravelEncounterRuntime:
    """Travel mode: MVP uses monsters, later can reuse the same discovery builders for rifts."""

    def __init__(self, *, policy: EncounterPolicy, monsters: MonsterDiscoveryBuilder | None = None) -> None:
        self._policy = policy
        self._monsters = monsters or MonsterDiscoveryBuilder()

    async def build(
        self,
        *,
        char_id: int,
        loc_id: str,
        tier: int,
        roll_type: str,
        difficulty: str,
        status: Any,
        gear_score: float,
        hunting_skill: float = 0.0,
        integration: EncounterIntegration,
    ) -> EncounterDTO | None:
        if roll_type == "monster":
            return await self._monsters.build(
                char_id=char_id,
                loc_id=loc_id,
                tier=tier,
                difficulty=difficulty,
                status=status,
                budget=self._policy.monster_budget(gear_score, hunting_skill=hunting_skill),
                hunting_skill=hunting_skill,
                integration=integration,
            )
        if roll_type == "rift":
            return await build_rift_placeholder(loc_id=loc_id)
        if roll_type == "merchant":
            return await build_merchant_placeholder(loc_id=loc_id)
        if roll_type == "resource":
            return await build_resource_placeholder(loc_id=loc_id)
        return None
