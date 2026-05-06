from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.character.integrations import CharacterSystemIntegrator


class CharacterSessionPersistenceService:
    def __init__(self, *, system_integrator: CharacterSystemIntegrator) -> None:
        self.system_integrator = system_integrator

    async def sync_active_session_to_db(self, char_id: int) -> dict[str, Any]:
        return await self.system_integrator.sync_active_session(char_id)
