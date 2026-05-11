from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.exploration.runtime.encounter.modes import EncounterMode
from src.backend.features.exploration.runtime.encounter.policy import EncounterPolicy
from src.backend.features.exploration.runtime.encounter.scouting import TerritoryScoutingRuntime
from src.backend.features.exploration.runtime.encounter.travel import TravelEncounterRuntime

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
    from src.shared.schemas.exploration import EncounterDTO


class EncounterEngine:
    """Routes encounter generation to mode runtimes."""

    def __init__(self, *, policy: EncounterPolicy | None = None, **_: Any) -> None:
        self._policy = policy or EncounterPolicy()
        self._travel = TravelEncounterRuntime(policy=self._policy)
        self._scouting = TerritoryScoutingRuntime(self._travel)

    async def try_generate_encounter(
        self,
        char_id: int,
        location_data: dict[str, Any],
        scouting_skill: float,
        trigger: str = "move",
        loc_id: str = "",
        *,
        mode: EncounterMode | str = EncounterMode.TRAVEL,
        gear_score: float = 0.0,
        encounter_integration: EncounterIntegration | None = None,
    ) -> EncounterDTO | None:
        flags = location_data.get("flags", {})
        flags = flags if isinstance(flags, dict) else {}
        anchor_influence = location_data.get("anchor_influence", {})
        anchor_influence = anchor_influence if isinstance(anchor_influence, dict) else {}
        if self._policy.is_safe_context(flags, anchor_influence):
            return None
        if encounter_integration is None:
            return None

        encounter_mode = EncounterMode(mode)
        if not self._policy.should_roll(mode=encounter_mode, trigger=trigger):
            return None

        tier = _safe_int(flags.get("threat_tier", 1), default=1)
        roll = self._policy.roll(mode=encounter_mode, tier=tier, scouting_skill=scouting_skill)
        runtime = self._travel if encounter_mode == EncounterMode.TRAVEL else self._scouting
        return await runtime.build(
            char_id=char_id,
            loc_id=loc_id,
            tier=tier,
            roll_type=roll.discovery_type,
            difficulty=roll.difficulty,
            status=roll.status,
            gear_score=gear_score,
            integration=encounter_integration,
        )


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
