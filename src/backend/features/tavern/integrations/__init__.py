from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.character.events import CharacterEvents
from src.backend.features.exploration.resources.service_registry import get_service_entry
from src.backend.features.tavern.resources import TavernConfig, get_tavern_config
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.features.tavern.models import CharacterTavernRoom
    from src.backend.features.tavern.repositories import TavernRoomRepository
    from src.backend.infrastructure.world.location_store import WorldLocationStore


class TavernSystemIntegrator:
    def __init__(
        self,
        *,
        character_sessions: CharacterSessionManager | None = None,
        world_store: WorldLocationStore | None = None,
        room_repository: TavernRoomRepository,
        events: GameEventProducer | None = None,
    ) -> None:
        self.character_sessions = character_sessions
        self.world_store = world_store
        self.room_repository = room_repository
        self.events = events

    async def enter_tavern(self, char_id: int) -> None:
        if self.character_sessions is None:
            return
        current_state = await self.character_sessions.get_section(char_id, "state")
        if current_state == CoreDomain.TAVERN.value:
            return
        await self.character_sessions.set_state(char_id, CoreDomain.TAVERN)

    async def leave_tavern(self, char_id: int) -> None:
        if self.character_sessions is None:
            return
        await self.character_sessions.set_state(char_id, CoreDomain.EXPLORATION, prev_state=CoreDomain.TAVERN)

    async def current_location_id(self, char_id: int) -> str | None:
        if self.character_sessions is None:
            return None
        location = await self.character_sessions.get_section(char_id, "location")
        return str(location.get("current")) if isinstance(location, dict) and location.get("current") else None

    async def resolve_tavern_config(
        self,
        char_id: int,
        *,
        tavern_id: str | None = None,
        service_id: str | None = None,
        location_id: str | None = None,
    ) -> tuple[TavernConfig, str | None]:
        resolved_location_id = location_id or await self.current_location_id(char_id)
        if tavern_id:
            return get_tavern_config(tavern_id), resolved_location_id

        if service_id:
            entry = get_service_entry(service_id)
            if entry is None:
                raise ValueError(f"Unknown tavern service_id: {service_id}")
            entry_tavern_id = str(entry.metadata.get("tavern_id") or "")
            return get_tavern_config(entry_tavern_id), resolved_location_id

        if resolved_location_id and self.world_store is not None:
            loc_data = await self.world_store.get_location(resolved_location_id)
            services = loc_data.get("services") if isinstance(loc_data, dict) else None
            if isinstance(services, list):
                for raw_service_id in services:
                    entry = get_service_entry(str(raw_service_id))
                    if entry is not None and entry.metadata.get("service_type") == "tavern":
                        return get_tavern_config(str(entry.metadata["tavern_id"])), resolved_location_id

        raise ValueError("Tavern context cannot be resolved for current character location")

    async def get_room(self, *, char_id: int, tavern_id: str) -> CharacterTavernRoom | None:
        return await self.room_repository.get_for_character(character_id=char_id, tavern_id=tavern_id)

    async def grant_room(
        self,
        *,
        char_id: int,
        tavern_id: str,
        room_key: str,
    ) -> tuple[CharacterTavernRoom, bool]:
        return await self.room_repository.grant_room(
            character_id=char_id,
            tavern_id=tavern_id,
            room_key=room_key,
        )

    async def restore_vitals(self, *, char_id: int, reason: str) -> dict[str, Any]:
        if self.events is None:
            raise RuntimeError("Tavern events producer is not configured")
        response = await self.events.request(
            CharacterEvents.VITALS_RESTORE_REQUESTED,
            {"char_id": char_id, "reason": reason},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Tavern vitals restore failed: {response!r}")
        vitals = response.get("vitals") or {}
        return vitals if isinstance(vitals, dict) else {}
