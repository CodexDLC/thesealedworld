from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

from src.backend.features.exploration.dto.result import ExplorationTransition
from src.backend.features.exploration.runtime.encounter import EncounterMode
from src.backend.features.exploration.runtime.encounter.bypass import (
    bypass_chance_percent,
    calculate_bypass_chance,
    encounter_with_bypass_chance,
)
from src.shared.enums import CoreDomain

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration
    from src.backend.features.exploration.runtime.encounter import EncounterEngine
    from src.backend.features.exploration.services.encounter_session_service import ExplorationEncounterSessionService
    from src.backend.features.exploration.services.navigation_service import ExplorationNavigationService
    from src.shared.schemas.exploration import EncounterDTO


class ExplorationEncounterService:
    """Coordinates active encounter state and encounter runtime generation."""

    def __init__(
        self,
        *,
        engine: EncounterEngine,
        integration: EncounterIntegration | None,
        session: ExplorationEncounterSessionService,
        navigation: ExplorationNavigationService,
    ) -> None:
        self._engine = engine
        self._integration = integration
        self._session = session
        self._navigation = navigation

    async def active_payload(self, char_id: int) -> EncounterDTO | None:
        encounter = await self._session.get_active(char_id)
        if encounter is None:
            return None
        encounter = await self._attach_bypass_chance(char_id, encounter)
        if isinstance(encounter.metadata.get("navigation"), dict):
            return encounter
        loc_id = await self._navigation.current_loc_id(char_id)
        loc_data = await self._navigation.location_data(loc_id)
        hydrated = await self._navigation.attach_navigation_snapshot(char_id, loc_id, loc_data, encounter)
        hydrated = await self._attach_bypass_chance(char_id, hydrated)
        try:
            await self._session.patch_payload(hydrated)
        except Exception:  # noqa: BLE001
            log.warning(
                "ExplorationEncounterService | active_snapshot_patch_failed char_id=%s encounter=%s",
                char_id,
                encounter.id,
            )
        return hydrated

    async def roll_travel(
        self,
        *,
        char_id: int,
        loc_id: str,
        loc_data: dict[str, Any],
    ) -> EncounterDTO | None:
        return await self._roll(
            char_id=char_id,
            loc_id=loc_id,
            loc_data=loc_data,
            mode=EncounterMode.TRAVEL,
            trigger="move",
        )

    async def roll_scouting(
        self,
        *,
        char_id: int,
        loc_id: str,
        loc_data: dict[str, Any],
    ) -> EncounterDTO | None:
        return await self._roll(
            char_id=char_id,
            loc_id=loc_id,
            loc_data=loc_data,
            mode=EncounterMode.TERRITORY_SCOUTING,
            trigger="search",
        )

    async def persist(self, char_id: int, encounter: EncounterDTO) -> None:
        await self._session.save(char_id, encounter)

    async def bypass(self, char_id: int, encounter: EncounterDTO) -> None:
        await self._session.clear(char_id, encounter.id)

    async def continue_from_placeholder(self, char_id: int, encounter: EncounterDTO) -> None:
        await self._session.clear(char_id, encounter.id)

    async def attack(self, char_id: int, encounter: EncounterDTO) -> ExplorationTransition | EncounterDTO:
        combat = dict(encounter.metadata.get("combat") or {})
        combat_id = combat.get("combat_id")
        status = combat.get("status")
        if status != "ready":
            combat = await self._retry_combat_request(combat, encounter)
            metadata = dict(encounter.metadata)
            metadata["combat"] = combat
            encounter = encounter.model_copy(update={"metadata": metadata, "session_id": combat.get("combat_id")})
            await self._session.patch_payload(encounter)
            combat_id = combat.get("combat_id")
            status = combat.get("status")

        if status != "ready" or not combat_id:
            return encounter

        await self._session.attach_combat(char_id, str(combat_id))
        await self._session.clear(char_id, encounter.id)
        return ExplorationTransition(
            char_id=char_id,
            target_state=CoreDomain.COMBAT,
            reason="exploration_attack",
            combat_id=str(combat_id),
            metadata={"encounter_id": encounter.id},
        )

    async def _roll(
        self,
        *,
        char_id: int,
        loc_id: str,
        loc_data: dict[str, Any],
        mode: EncounterMode,
        trigger: str,
    ) -> EncounterDTO | None:
        if self._integration is None:
            return None
        skills = await self._integration.get_ac_skill_snapshot(char_id)
        gear_score = await self._gear_score(char_id)
        encounter = await self._engine.try_generate_encounter(
            char_id=char_id,
            location_data=loc_data,
            scouting_skill=skills.skill_scouting,
            trigger=trigger,
            loc_id=loc_id,
            mode=mode,
            gear_score=gear_score,
            encounter_integration=self._integration,
        )
        if encounter is None:
            return None
        return encounter_with_bypass_chance(encounter, calculate_bypass_chance(skills))

    async def attempt_bypass(self, char_id: int, encounter: EncounterDTO) -> tuple[bool, EncounterDTO | None, int]:
        skills = await self._skill_snapshot(char_id)
        chance = calculate_bypass_chance(skills)
        chance_percent = bypass_chance_percent(chance)
        roll = random.random()
        if roll <= chance:
            await self._session.clear(char_id, encounter.id)
            return True, None, chance_percent

        updated = encounter_with_bypass_chance(
            encounter,
            chance,
            result={
                "success": False,
                "chance_percent": chance_percent,
                "roll_percent": bypass_chance_percent(roll),
            },
        )
        await self._session.patch_payload(updated)
        return False, updated, chance_percent

    async def _retry_combat_request(self, combat: dict[str, Any], encounter: EncounterDTO) -> dict[str, Any]:
        request = combat.get("request")
        if self._integration is None or not isinstance(request, dict):
            return combat
        try:
            response = await self._integration.request_combat_session(request, correlation_id=encounter.id)
        except Exception as exc:  # noqa: BLE001
            response = {
                "status": "failed",
                "combat_id": request.get("combat_id"),
                "error": f"{exc.__class__.__name__}: {exc}",
            }
        return {
            "status": response.get("status") or "requested",
            "combat_id": response.get("combat_id") or request.get("combat_id"),
            "request": request,
            "response": response,
        }

    async def _gear_score(self, char_id: int) -> float:
        if self._integration is None:
            return 0.0
        metrics = await self._integration.character_sessions.get_section(char_id, "metrics")
        if not isinstance(metrics, dict):
            return 0.0
        try:
            return max(0.0, float(metrics.get("gear_score") or 0.0))
        except (TypeError, ValueError):
            return 0.0

    async def _attach_bypass_chance(self, char_id: int, encounter: EncounterDTO) -> EncounterDTO:
        skills = await self._skill_snapshot(char_id)
        return encounter_with_bypass_chance(encounter, calculate_bypass_chance(skills))

    async def _skill_snapshot(self, char_id: int) -> Any:
        if self._integration is None:
            return {}
        return await self._integration.get_ac_skill_snapshot(char_id)
