from typing import Any

from loguru import logger

from src.backend.core.auth import User
from src.backend.features.game_lobby.integrations import GameLobbyIntegration
from src.shared.enums import CoreDomain
from src.shared.schemas import (
    CoreResponseDTO,
    GameLobbyPayloadDTO,
    GameLobbyPopulationStatsDTO,
    GameStateHeader,
    LobbySlotDTO,
)


class GameLobbyService:
    MAX_SLOTS = 4

    def __init__(self, integration: GameLobbyIntegration) -> None:
        self.integration = integration

    async def get_start_payload(self, user: User) -> GameLobbyPayloadDTO:
        characters = await self.integration.list_user_characters(user.id)

        occupied_count = len(characters)
        logger.bind(user_id=str(user.id), occupied_slot_count=occupied_count).debug("LobbyPayloadBuilt")

        occupied_slots = [
            LobbySlotDTO(
                index=index,
                is_empty=False,
                character_id=str(character.character_id),
                name=character.name,
                avatar_url=character.avatar_url,
                status=character.status,
                presence_status=character.presence_status,
                location_id=character.location_id,
                updated_at=character.updated_at,
                vitals=character.vitals or {},
                attributes=character.attributes or {},
                equipped_items=character.equipped_items or [],
                inventory_summary=character.inventory_summary or {},
                skills=character.skills or [],
            )
            for index, character in enumerate(characters, start=1)
        ]

        # Fill remaining slots up to MAX_SLOTS
        empty_slots = []
        for index in range(occupied_count + 1, self.MAX_SLOTS + 1):
            empty_slots.append(LobbySlotDTO(index=index, is_empty=True, status="VACANT"))

        return GameLobbyPayloadDTO(
            can_start=occupied_count < self.MAX_SLOTS,
            slots=[*occupied_slots, *empty_slots],
            max_slots=self.MAX_SLOTS,
        )

    async def get_population_stats(self) -> GameLobbyPopulationStatsDTO:
        return GameLobbyPopulationStatsDTO(characters_total=await self.integration.count_all_characters())

    async def delete_character(
        self,
        user: User,
        character_id: int,
        *,
        confirm_name: str,
    ) -> None:
        await self.integration.delete_owned_character(
            user_id=user.id,
            character_id=character_id,
            confirm_name=confirm_name,
        )

    async def enter_character(self, user: User, character_id: int) -> CoreResponseDTO[dict[str, Any]]:
        await self.integration.release_other_active_sessions(user.id, character_id)
        session_doc = await self.integration.bootstrap_active_character(user_id=user.id, character_id=character_id)
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.LOBBY),
            payload={"character_id": session_doc.char_id, "state": str(session_doc.state)},
            payload_type="active_character_bootstrap",
        )

    async def release_character(self, user: User, character_id: int) -> CoreResponseDTO[dict[str, Any]]:
        await self.integration.release_active_character(user_id=user.id, character_id=character_id)
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.LOBBY),
            payload={"character_id": character_id, "released": True},
            payload_type="active_character_release",
        )
