from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, StateTransitionDTO

if TYPE_CHECKING:
    from src.backend.core.auth import User
    from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO, CharacterSessionRefsDTO
    from src.backend.features.game_session.integrations import GameSessionIntegrator


GameplayEntryResponse = CoreResponseDTO[StateTransitionDTO | dict[str, Any]]


class GameSessionService:
    """Routes an already selected active character to the first gameplay screen."""

    MAIN_SCREEN_STATES = {
        CoreDomain.SCENARIO,
        CoreDomain.COMBAT,
        CoreDomain.COMBAT_RESULT,
        CoreDomain.ARENA,
        CoreDomain.TAVERN,
        CoreDomain.EXPLORATION,
        CoreDomain.DEATH,
        CoreDomain.LOOT,
    }

    def __init__(self, *, integrator: GameSessionIntegrator) -> None:
        self.integrator = integrator

    async def enter_character(self, user: User, character_id: int) -> GameplayEntryResponse:
        session_doc = await self.integrator.get_active_session(character_id, user.id)
        if session_doc is None:
            response = self._lobby_response(char_id=character_id, reason="active_character_unavailable")
            self._log_enter_response(char_id=character_id, response=response)
            return response

        return await self._enter_from_active_session(session_doc)

    async def _enter_from_active_session(self, session_doc: CharacterSessionDocumentDTO) -> GameplayEntryResponse:
        current_state = self._state_or_none(session_doc.state)
        previous_state = self._state_or_none(session_doc.prev_state)

        selected_state = self._pending_combat_result_state(session_doc)
        route_reason = "combat_result_pending" if selected_state is not None else "current_state"
        if selected_state is not None and current_state != selected_state:
            await self.integrator.set_active_session_state(session_doc.char_id, selected_state)

        if selected_state is None:
            selected_state = self._valid_routing_state(session_doc, current_state)

        if selected_state is None and previous_state is not None:
            selected_state = self._valid_routing_state(session_doc, previous_state)
            if selected_state is not None:
                route_reason = "previous_state_fallback"
                await self.integrator.set_active_session_state(session_doc.char_id, selected_state)

        if selected_state is None:
            selected_state = CoreDomain.EXPLORATION
            route_reason = "reset_to_exploration"
            await self.integrator.reset_active_session_to_exploration(session_doc.char_id)

        response = self._state_response(
            session_doc=session_doc,
            current_state=selected_state,
            previous_state=previous_state,
            route_reason=route_reason,
        )
        self._log_enter_response(char_id=session_doc.char_id, response=response)
        return response

    @staticmethod
    def _pending_combat_result_state(session_doc: CharacterSessionDocumentDTO) -> CoreDomain | None:
        if session_doc.sessions.combat_finalization_id:
            return CoreDomain.COMBAT_RESULT
        return None

    def _valid_routing_state(
        self,
        session_doc: CharacterSessionDocumentDTO,
        state: CoreDomain | None,
    ) -> CoreDomain | None:
        if state not in self.MAIN_SCREEN_STATES:
            return None
        if state == CoreDomain.EXPLORATION:
            return state if session_doc.location.current else None
        return state if self._required_ref_present(session_doc.sessions, state) else None

    @staticmethod
    def _required_ref_present(sessions: CharacterSessionRefsDTO, state: CoreDomain) -> bool:
        if state == CoreDomain.SCENARIO:
            return bool(sessions.scenario_id)
        if state == CoreDomain.COMBAT:
            return bool(sessions.combat_id)
        if state == CoreDomain.COMBAT_RESULT:
            return bool(sessions.combat_finalization_id)
        if state == CoreDomain.ARENA:
            return bool(sessions.arena_id)
        if state == CoreDomain.DEATH:
            return bool(sessions.death_run_id)
        if state == CoreDomain.LOOT:
            return bool(sessions.post_combat)
        return True

    async def respawn_character(self, user: User, character_id: int) -> GameplayEntryResponse:
        session_doc = await self.integrator.get_active_session(character_id, user.id)
        if session_doc is None:
            return self._lobby_response(char_id=character_id, reason="active_character_unavailable")
        if self._state_or_none(session_doc.state) != CoreDomain.DEATH:
            return self._state_response(
                session_doc=session_doc,
                current_state=self._state_or_none(session_doc.state) or CoreDomain.EXPLORATION,
                previous_state=self._state_or_none(session_doc.prev_state),
                route_reason="respawn_not_required",
            )

        result = await self.integrator.respawn_character(character_id)
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.DEATH),
            payload=StateTransitionDTO(
                char_id=character_id,
                target_state=CoreDomain.EXPLORATION,
                reason=str(result.get("status") or "respawned"),
                metadata=result,
            ),
            payload_type="state_transition",
        )

    async def claim_post_combat_loot(
        self,
        user: User,
        character_id: int,
        corpse_ids: list[str],
    ) -> GameplayEntryResponse:
        session_doc = await self.integrator.get_active_session(character_id, user.id)
        if session_doc is None:
            return self._lobby_response(char_id=character_id, reason="active_character_unavailable")
        result = await self.integrator.claim_post_combat_loot(character_id, corpse_ids)
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.LOOT),
            payload=StateTransitionDTO(
                char_id=character_id,
                target_state=CoreDomain.EXPLORATION,
                reason=str(result.get("status") or "loot_claimed"),
                metadata=result,
            ),
            payload_type="state_transition",
        )

    @staticmethod
    def _state_or_none(value: str | CoreDomain | None) -> CoreDomain | None:
        if value is None:
            return None
        if isinstance(value, CoreDomain):
            return value
        text = str(value).strip()
        if text.startswith("CoreDomain."):
            text = text.rsplit(".", maxsplit=1)[-1]
        try:
            return CoreDomain(text.lower())
        except ValueError:
            try:
                return CoreDomain[text.upper()]
            except KeyError:
                logger.warning("Unknown active character state: state={}", value)
                return None

    @staticmethod
    def _state_response(
        *,
        session_doc: CharacterSessionDocumentDTO,
        current_state: CoreDomain,
        previous_state: CoreDomain | None,
        route_reason: str,
    ) -> GameplayEntryResponse:
        return CoreResponseDTO(
            header=GameStateHeader(current_state=current_state, previous_state=previous_state),
            payload={
                "character_id": session_doc.char_id,
                "name": session_doc.bio.name,
                "domain": current_state.value,
                "source": "hot_ac",
                "route_reason": route_reason,
            },
            payload_type=f"{current_state.value}_session",
        )

    @staticmethod
    def _lobby_response(*, char_id: int, reason: str) -> GameplayEntryResponse:
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.LOBBY),
            payload=StateTransitionDTO(char_id=char_id, target_state=CoreDomain.LOBBY, reason=reason),
            payload_type="state_transition",
        )

    @staticmethod
    def _log_enter_response(*, char_id: int, response: GameplayEntryResponse) -> None:
        logger.bind(
            char_id=char_id,
            current_state=response.header.current_state.value,
            previous_state=response.header.previous_state.value if response.header.previous_state else None,
            payload_type=response.payload_type,
            transaction_id=response.header.transaction_id,
        ).info("Game session entry routed")
