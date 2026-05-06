from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.features.game_lobby.integrations import GameLobbyIntegration
    from src.backend.features_site.auth.models import User
    from src.shared.schemas import CreateCharacterRequestDTO, ScenarioPayloadDTO


class CharacterCreationService:
    MAX_SLOTS = 4
    INITIAL_LOCATION_ID = "52_52"

    def __init__(
        self,
        integration: GameLobbyIntegration,
    ) -> None:
        self.integration = integration

    async def create_and_enter(
        self,
        user: User,
        dto: CreateCharacterRequestDTO,
    ) -> ScenarioPayloadDTO:
        logger.info("Character creation started: user_id={}", user.id)
        await self._ensure_slot_available(user)

        # Determine default avatar based on gender if none provided
        avatar_url = dto.avatar
        if not avatar_url:
            if dto.gender == "female":
                avatar_url = "/static/images/avatars/silhouette_f.png"
            else:
                avatar_url = "/static/images/avatars/silhouette_m.png"

        character = await self.integration.create_character(
            user_id=user.id,
            name=dto.name,
            gender=dto.gender,
            avatar_url=avatar_url,
            game_stage="session_pending",
            prev_game_stage=CoreDomain.LOBBY.value,
            location_id=self.INITIAL_LOCATION_ID,
        )
        char_id = character.character_id

        try:
            await self.integration.create_active_session(character)
            payload = await self.integration.initialize_starting_scenario(
                char_id,
                "awakening_rift",
                source="onboarding",
            )
        except Exception:
            logger.exception("Character creation failed; cleanup started: char_id={} user_id={}", char_id, user.id)
            await self.integration.cleanup_failed_character_creation(char_id)
            logger.warning("Character creation cleanup finished: char_id={} user_id={}", char_id, user.id)
            raise

        payload.extra_data = {
            **(getattr(payload, "extra_data", None) or {}),
            "char_id": char_id,
            "quest_key": "awakening_rift",
        }
        await self.integration.mark_character_entered_scenario(char_id)
        logger.info("Character entered scenario: char_id={} user_id={}", char_id, user.id)
        return payload

    async def _ensure_slot_available(self, user: User) -> None:
        characters_count = await self.integration.count_user_characters(user.id)
        if characters_count >= self.MAX_SLOTS:
            logger.warning("Character creation rejected: slot_limit user_id={} count={}", user.id, characters_count)
            raise BusinessLogicException("Character slot limit reached")
