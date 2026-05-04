from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.scenario.exceptions import ScenarioSessionNotFound
from src.backend.infrastructure.actor_state import CharacterRepository
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, ScenarioPayloadDTO

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.scenario.services import ScenarioService
    from src.backend.features_site.auth.models import User


class GameSessionService:
    """Owns entry into the active game session for a character."""

    STARTING_QUEST_KEY = "awakening_rift"
    SCENARIO_ENTRY_STAGES = {
        "",
        CoreDomain.LOBBY.value,
        CoreDomain.SCENARIO.value,
        CoreDomain.ONBOARDING.value,
        "SESSION_PENDING",
    }

    def __init__(self, *, db_session: AsyncSession, scenario_service: ScenarioService) -> None:
        self.db_session = db_session
        self.scenario_service = scenario_service

    async def enter_character(
        self, user: User, character_id: int
    ) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
        character = await self._get_owned_character_or_raise(user, character_id)
        char_id = character.character_id
        stage = (character.game_stage or "").upper()
        previous_state = self._state_from_stage_or_none(getattr(character, "prev_game_stage", None))

        if stage in self.SCENARIO_ENTRY_STAGES:
            payload = await self._resume_or_initialize_scenario(char_id)
            response: CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]] = CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.SCENARIO, previous_state=previous_state),
                payload=payload,
                payload_type="scenario_screen",
            )
            self._log_enter_response(char_id=char_id, response=response)
            return response

        current_state = self._state_from_stage(stage)
        response = CoreResponseDTO(
            header=GameStateHeader(current_state=current_state, previous_state=previous_state),
            payload={
                "character_id": char_id,
                "name": character.name,
                "stage": character.game_stage,
                "domain": current_state.value,
            },
            payload_type=f"{current_state.value.lower()}_session",
        )
        self._log_enter_response(char_id=char_id, response=response)
        return response

    async def _resume_or_initialize_scenario(self, char_id: int) -> ScenarioPayloadDTO:
        try:
            payload = await self.scenario_service.resume(char_id)
        except ScenarioSessionNotFound:
            payload = await self.scenario_service.initialize(char_id, self.STARTING_QUEST_KEY, source="session_enter")
            character = await CharacterRepository(self.db_session).get_by_id(char_id)
            if character is not None:
                character.game_stage = CoreDomain.SCENARIO.value.lower()
                character.prev_game_stage = CoreDomain.LOBBY.value.lower()
                await self.db_session.commit()

        payload.extra_data = {
            **(payload.extra_data or {}),
            "char_id": char_id,
            "quest_key": (payload.extra_data or {}).get("quest_key", self.STARTING_QUEST_KEY),
        }
        logger.info("Game session scenario payload resolved: char_id={} node={}", char_id, payload.node_key)
        return payload

    async def _get_owned_character_or_raise(self, user: User, character_id: int):
        character = await CharacterRepository(self.db_session).get_by_id_and_user_id(character_id, user.id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")
        return character

    @staticmethod
    def _state_from_stage(stage: str) -> CoreDomain:
        try:
            return CoreDomain(stage)
        except ValueError:
            logger.warning("Unknown character game stage; falling back to EXPLORATION: stage={}", stage)
            return CoreDomain.EXPLORATION

    @staticmethod
    def _state_from_stage_or_none(stage: str | None) -> CoreDomain | None:
        if not stage:
            return None
        try:
            return CoreDomain(stage.upper())
        except ValueError:
            logger.warning("Unknown previous game stage; omitting previous_state: stage={}", stage)
            return None

    @staticmethod
    def _log_enter_response(
        *,
        char_id: int,
        response: CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]],
    ) -> None:
        logger.bind(
            char_id=char_id,
            current_state=response.header.current_state.value,
            previous_state=response.header.previous_state.value if response.header.previous_state else None,
            payload_type=response.payload_type,
            transaction_id=response.header.transaction_id,
        ).info("Game session entered")
