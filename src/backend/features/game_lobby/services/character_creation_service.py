from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.moderation import CharacterNamePolicy
from src.shared.enums import CoreDomain
from src.shared.schemas import CharacterNameAvailabilityDTO
from src.shared.utils.character_name import CharacterNameError

if TYPE_CHECKING:
    from src.backend.core.auth import User
    from src.backend.features.game_lobby.integrations import GameLobbyIntegration
    from src.shared.schemas import CreateCharacterRequestDTO, ScenarioPayloadDTO


class CharacterCreationService:
    MAX_SLOTS = 4
    INITIAL_LOCATION_ID = "52_52"
    INITIAL_NPC_KEY = "portal_pad_guide"

    def __init__(
        self,
        integration: GameLobbyIntegration,
        name_policy: CharacterNamePolicy | None = None,
    ) -> None:
        self.integration = integration
        self.name_policy = name_policy or CharacterNamePolicy()

    async def check_name_availability(self, value: str) -> CharacterNameAvailabilityDTO:
        name, code, message = self.name_policy.check(value)
        if name is None:
            return CharacterNameAvailabilityDTO(available=False, code=code, message=message)
        if await self.integration.character_name_exists(name.key):
            return CharacterNameAvailabilityDTO(
                available=False,
                name=name.display,
                name_key=name.key,
                code="name_taken",
                message="Имя уже занято",
            )
        return CharacterNameAvailabilityDTO(available=True, name=name.display, name_key=name.key)

    async def create_and_enter(
        self,
        user: User,
        dto: CreateCharacterRequestDTO,
    ) -> ScenarioPayloadDTO:
        logger.bind(user_id=str(user.id)).info("CharacterCreationStarted")
        try:
            name = self.name_policy.validate(dto.name)
        except CharacterNameError as exc:
            raise BusinessLogicException(exc.message) from exc
        if await self.integration.character_name_exists(name.key):
            raise BusinessLogicException("Имя уже занято")

        await self._ensure_slot_available(user)

        # Determine default avatar based on gender if none provided
        avatar_url = dto.avatar
        if not avatar_url:
            if dto.gender == "female":
                avatar_url = "/static/images/avatars/silhouette_f.webp"
            else:
                avatar_url = "/static/images/avatars/silhouette_m.webp"

        character = await self.integration.create_character(
            user_id=user.id,
            name=name.display,
            name_key=name.key,
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
                npc_key=self.INITIAL_NPC_KEY,
            )
        except Exception:
            logger.bind(char_id=char_id, user_id=str(user.id)).exception("CharacterCreationFailed")
            await self.integration.cleanup_failed_character_creation(char_id)
            logger.bind(char_id=char_id, user_id=str(user.id)).warning("CharacterCreationCleanupFinished")
            raise

        await self.integration.release_other_active_sessions(user.id, char_id)
        payload.extra_data = {
            **(getattr(payload, "extra_data", None) or {}),
            "char_id": char_id,
            "quest_key": "awakening_rift",
        }
        await self.integration.mark_character_entered_scenario(char_id)
        logger.bind(char_id=char_id, user_id=str(user.id)).info("CharacterEnteredScenario")
        return payload

    async def _ensure_slot_available(self, user: User) -> None:
        characters_count = await self.integration.count_user_characters(user.id)
        if characters_count >= self.MAX_SLOTS:
            logger.bind(user_id=str(user.id), character_count=characters_count, reason="slot_limit").warning(
                "CharacterCreationRejected"
            )
            raise BusinessLogicException("Лимит персонажей достигнут")
