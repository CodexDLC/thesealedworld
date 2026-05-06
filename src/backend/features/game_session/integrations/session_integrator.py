from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.backend.features.scenario.exceptions import ScenarioSessionNotFound
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.features.scenario.services import ScenarioService
    from src.shared.schemas import ScenarioPayloadDTO


@dataclass(frozen=True, slots=True)
class GameSessionCharacter:
    character_id: int
    name: str
    game_stage: str | None
    prev_game_stage: str | None


class GameSessionIntegrator:
    """Facade over character persistence and scenario feature entrypoints."""

    def __init__(
        self,
        *,
        character_repo: CharacterRepository | None = None,
        character_sessions: CharacterSessionManager | None = None,
        db_session: AsyncSession | None = None,
        scenario_service: ScenarioService,
    ) -> None:
        if character_repo is None:
            if db_session is None:
                raise ValueError("character_repo or db_session is required")
            character_repo = CharacterRepository(db_session)
        self.character_repo = character_repo
        self.character_sessions = character_sessions
        self.scenario_service = scenario_service

    async def get_owned_character(self, character_id: int, user_id: UUID) -> GameSessionCharacter | None:
        character = await self.character_repo.get_by_id_and_user_id(character_id, user_id)
        if character is None:
            return None
        return GameSessionCharacter(
            character_id=character.character_id,
            name=character.name,
            game_stage=character.game_stage,
            prev_game_stage=character.prev_game_stage,
        )

    async def release_other_active_sessions(self, user_id: UUID, selected_character_id: int) -> None:
        if self.character_sessions is None:
            return

        characters = await self.character_repo.get_by_user_id(user_id)
        other_character_ids = [
            character.character_id for character in characters if character.character_id != selected_character_id
        ]
        if not other_character_ids:
            return

        sessions = await self.character_sessions.get_sessions_batch(other_character_ids)
        persisted_any = False
        for character_id, document in sessions.items():
            if not isinstance(document, dict):
                continue

            await self._persist_active_session_snapshot(character_id, document)
            persisted_any = True
            await self.scenario_service.cleanup(character_id)
            await self.character_sessions.delete_session(character_id)
            logger.info(
                "Released previous active character session: user_id={} selected_char_id={} released_char_id={}",
                user_id,
                selected_character_id,
                character_id,
            )

        if persisted_any:
            await self.character_repo.commit()

    async def get_active_session(self, character_id: int, user_id: UUID) -> CharacterSessionDocumentDTO | None:
        if self.character_sessions is None:
            return None

        document = await self.character_sessions.get_session(character_id)
        if document is None:
            return None

        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.warning("Game session hot AC validation failed: char_id={}", character_id, exc_info=True)
            return None

        if session_doc.user_id != user_id:
            logger.warning(
                "Game session hot AC ownership mismatch: char_id={} owner={} requested_by={}",
                character_id,
                session_doc.user_id,
                user_id,
            )
            return None

        return session_doc

    async def _persist_active_session_snapshot(self, character_id: int, document: dict[str, object]) -> None:
        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.warning(
                "Skipping invalid active session snapshot before release: char_id={}", character_id, exc_info=True
            )
            return

        synced = await self.character_repo.sync_active_session_snapshot(character_id, session_doc)
        if synced is None:
            logger.warning("Skipping active session snapshot sync; character missing: char_id={}", character_id)

    async def resume_or_initialize_scenario(
        self,
        char_id: int,
        *,
        quest_key: str,
        source: str,
        previous_state: CoreDomain = CoreDomain.LOBBY,
    ) -> ScenarioPayloadDTO:
        try:
            payload = await self.scenario_service.resume(char_id)
        except ScenarioSessionNotFound:
            payload = await self.scenario_service.initialize(char_id, quest_key, source=source)
            await self.set_character_state(char_id, CoreDomain.SCENARIO, previous_state=previous_state)

        payload.extra_data = {
            **(payload.extra_data or {}),
            "char_id": char_id,
            "quest_key": (payload.extra_data or {}).get("quest_key", quest_key),
        }
        logger.info("Game session scenario payload resolved: char_id={} node={}", char_id, payload.node_key)
        return payload

    async def set_character_state(
        self,
        char_id: int,
        state: CoreDomain,
        *,
        previous_state: CoreDomain | str | None = None,
    ) -> None:
        updated = await self.character_repo.set_character_state(
            char_id,
            state.value,
            prev_game_stage=self._state_value(previous_state),
        )
        if not updated:
            logger.warning("Game session persistent state update skipped; character missing: char_id={}", char_id)
            return

        await self.character_repo.commit()

    @staticmethod
    def _state_value(state: CoreDomain | str | None) -> str | None:
        if state is None:
            return None
        return state.value if isinstance(state, CoreDomain) else state
