from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, ScenarioPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
    from src.backend.features.game_session.integrations import GameSessionIntegrator
    from src.backend.features_site.auth.models import User


class GameSessionService:
    """Owns entry into the active game session for a character."""

    STARTING_QUEST_KEY = "awakening_rift"
    SCENARIO_ENTRY_STAGES = {
        "",
        CoreDomain.LOBBY.value,
        CoreDomain.SCENARIO.value,
        CoreDomain.ONBOARDING.value,
        "session_pending",
    }

    def __init__(self, *, integrator: GameSessionIntegrator) -> None:
        self.integrator = integrator

    async def enter_character(
        self, user: User, character_id: int
    ) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
        character = await self._get_owned_character_or_raise(user, character_id)
        char_id = character.character_id
        await self.integrator.release_other_active_sessions(user.id, char_id)
        active_session = await self.integrator.get_active_session(char_id, user.id)
        if active_session is not None:
            return await self._enter_from_active_session(active_session)

        stage = self._normalize_stage_text(character.game_stage)
        previous_state = self._state_from_stage_or_none(getattr(character, "prev_game_stage", None))
        return await self._enter_from_stage(
            char_id=char_id,
            name=character.name,
            stage=stage,
            previous_state=previous_state,
            raw_stage=character.game_stage,
        )

    async def _enter_from_active_session(
        self, session_doc: CharacterSessionDocumentDTO
    ) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
        stage = self._normalize_stage_text(session_doc.state)
        previous_state = self._state_from_stage_or_none(session_doc.prev_state)
        return await self._enter_from_stage(
            char_id=session_doc.char_id,
            name=session_doc.bio.name,
            stage=stage,
            previous_state=previous_state,
            raw_stage=stage,
            source="hot_ac",
        )

    async def _enter_from_stage(
        self,
        *,
        char_id: int,
        name: str,
        stage: str,
        previous_state: CoreDomain | None,
        raw_stage: str | None,
        source: str = "persistent",
    ) -> CoreResponseDTO[ScenarioPayloadDTO | dict[str, Any]]:
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
                "name": name,
                "stage": raw_stage,
                "domain": current_state.value,
                "source": source,
            },
            payload_type=f"{current_state.value}_session",
        )
        self._log_enter_response(char_id=char_id, response=response)
        return response

    async def _resume_or_initialize_scenario(self, char_id: int) -> ScenarioPayloadDTO:
        return await self.integrator.resume_or_initialize_scenario(
            char_id,
            quest_key=self.STARTING_QUEST_KEY,
            source="session_enter",
            previous_state=CoreDomain.LOBBY,
        )

    async def _get_owned_character_or_raise(self, user: User, character_id: int):
        character = await self.integrator.get_owned_character(character_id, user.id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")
        return character

    @staticmethod
    def _state_from_stage(stage: str | CoreDomain) -> CoreDomain:
        try:
            return CoreDomain(GameSessionService._normalize_stage_text(stage))
        except ValueError:
            logger.warning("Unknown character game stage; falling back to EXPLORATION: stage={}", stage)
            return CoreDomain.EXPLORATION

    @staticmethod
    def _state_from_stage_or_none(stage: str | CoreDomain | None) -> CoreDomain | None:
        if not stage:
            return None
        try:
            return CoreDomain(GameSessionService._normalize_stage_text(stage))
        except ValueError:
            logger.warning("Unknown previous game stage; omitting previous_state: stage={}", stage)
            return None

    @staticmethod
    def _normalize_stage_text(stage: str | CoreDomain | None) -> str:
        if stage is None:
            return ""
        if isinstance(stage, CoreDomain):
            return stage.value
        text = str(stage).strip()
        if text.startswith("CoreDomain."):
            return text.rsplit(".", maxsplit=1)[-1].lower()
        return text.lower()

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
