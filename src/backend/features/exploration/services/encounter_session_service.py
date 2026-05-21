from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as log
from pydantic import ValidationError

from src.shared.schemas.exploration import EncounterDTO

if TYPE_CHECKING:
    from src.backend.features.exploration.integrations.encounter_integration import EncounterIntegration


class ExplorationEncounterSessionService:
    """Persists and restores active encounter sessions."""

    def __init__(self, integration: EncounterIntegration | None) -> None:
        self._integration = integration

    @property
    def enabled(self) -> bool:
        return self._integration is not None

    async def get_active(self, char_id: int) -> EncounterDTO | None:
        if self._integration is None:
            return None
        encounter_id = await self._integration.get_active_encounter_id(char_id)
        if encounter_id is None:
            return None
        session = await self._integration.get_encounter_session(encounter_id)
        if session is None:
            log.bind(char_id=char_id, encounter_id=encounter_id).warning("ExplorationEncounterStaleRef")
            await self._integration.detach_encounter_session(char_id)
            return None
        payload = session.get("payload", session)
        if not isinstance(payload, dict):
            await self.clear(char_id, encounter_id)
            return None
        try:
            return EncounterDTO.model_validate(payload)
        except ValidationError:
            log.bind(char_id=char_id, encounter_id=encounter_id).warning("ExplorationEncounterInvalidPayload")
            await self.clear(char_id, encounter_id)
            return None

    async def save(self, char_id: int, encounter: EncounterDTO) -> None:
        if self._integration is None:
            return
        payload = encounter.model_dump(mode="json")
        await self._integration.create_encounter_session(
            encounter.id,
            {
                "encounter_id": encounter.id,
                "char_id": char_id,
                "status": "pending",
                "payload": payload,
            },
        )
        await self._integration.attach_encounter_session(char_id, encounter.id)

    async def patch_payload(self, encounter: EncounterDTO) -> None:
        if self._integration is None:
            return
        await self._integration.patch_encounter_session(
            encounter.id,
            {"payload": encounter.model_dump(mode="json")},
        )

    async def clear(self, char_id: int, encounter_id: str) -> None:
        if self._integration is None:
            return
        await self._integration.clear_encounter_session(encounter_id)
        await self._integration.detach_encounter_session(char_id)

    async def attach_combat(self, char_id: int, combat_id: str) -> None:
        if self._integration is None:
            raise RuntimeError("Encounter integration is required to attach combat")
        await self._integration.attach_combat_session(char_id, combat_id)
