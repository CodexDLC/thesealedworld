from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
    from src.backend.features.exploration.runtime.encounter.travel import TravelEncounterRuntime
    from src.shared.schemas.exploration import EncounterDTO


class TerritoryScoutingRuntime:
    """Territory scouting reuses discovery builders, but can use different weights and UI later."""

    def __init__(self, travel_runtime: TravelEncounterRuntime) -> None:
        self._travel_runtime = travel_runtime

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
        location_threat: float = 0.0,
        hunting_skill: float = 0.0,
        integration: EncounterIntegration,
    ) -> EncounterDTO | None:
        return await self._travel_runtime.build(
            char_id=char_id,
            loc_id=loc_id,
            tier=tier,
            roll_type=roll_type,
            difficulty=difficulty,
            status=status,
            gear_score=gear_score,
            location_threat=location_threat,
            hunting_skill=hunting_skill,
            integration=integration,
        )
