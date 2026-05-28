from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.character.events import CharacterEvents
from src.backend.features.city_services.resources import (
    CityServiceDefinition,
    get_city_service_definition,
    get_tavern_definition,
)
from src.backend.features.exploration.resources.service_registry import get_service_entry
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.city_services.models import CharacterTavernRoom
    from src.backend.features.city_services.repositories import TavernRoomRepository
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager
    from src.backend.infrastructure.world.location_store import WorldLocationStore


class CityServiceSystemIntegrator:
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

    async def enter_city_service(self, char_id: int) -> None:
        if self.character_sessions is None:
            return
        current_state = await self.character_sessions.get_section(char_id, "state")
        if current_state == CoreDomain.CITY_SERVICES.value:
            return
        await self.character_sessions.set_state(char_id, CoreDomain.CITY_SERVICES)

    async def leave_city_service(self, char_id: int) -> None:
        if self.character_sessions is None:
            return
        await self.character_sessions.set_state(
            char_id,
            CoreDomain.EXPLORATION,
            prev_state=CoreDomain.CITY_SERVICES,
        )

    async def current_location_id(self, char_id: int) -> str | None:
        if self.character_sessions is None:
            return None
        location = await self.character_sessions.get_section(char_id, "location")
        return str(location.get("current")) if isinstance(location, dict) and location.get("current") else None

    async def resolve_service_definition(
        self,
        char_id: int,
        *,
        service_id: str | None = None,
        tavern_id: str | None = None,
        location_id: str | None = None,
    ) -> tuple[CityServiceDefinition, str | None]:
        resolved_location_id = location_id or await self.current_location_id(char_id)
        if service_id:
            return get_city_service_definition(service_id), resolved_location_id
        if tavern_id:
            return get_tavern_definition(tavern_id), resolved_location_id

        if resolved_location_id and self.world_store is not None:
            loc_data = await self.world_store.get_location(resolved_location_id)
            services = loc_data.get("services") if isinstance(loc_data, dict) else None
            if isinstance(services, list):
                for raw_service_id in services:
                    entry = get_service_entry(str(raw_service_id))
                    if entry is not None and entry.target_state == CoreDomain.CITY_SERVICES:
                        return get_city_service_definition(str(raw_service_id)), resolved_location_id

        raise ValueError("City service context cannot be resolved for current character location")

    async def get_tavern_room(self, *, char_id: int, tavern_id: str) -> CharacterTavernRoom | None:
        return await self.room_repository.get_for_character(character_id=char_id, tavern_id=tavern_id)

    async def grant_tavern_room(
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
            raise RuntimeError("City service events producer is not configured")
        response = await self.events.request(
            CharacterEvents.VITALS_RESTORE_REQUESTED,
            {"char_id": char_id, "reason": reason},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"City service vitals restore failed: {response!r}")
        vitals = response.get("vitals") or {}
        return vitals if isinstance(vitals, dict) else {}
