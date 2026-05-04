from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.arena.dto.session import ArenaCombatRequestDTO
    from src.backend.infrastructure.actor_state import CharacterSessionManager


class ArenaSystemIntegrator:
    COMBAT_SESSION_REQUESTED = "combat.session_requested"

    def __init__(self, *, events: GameEventProducer, character_sessions: CharacterSessionManager) -> None:
        self.events = events
        self.character_sessions = character_sessions

    async def request_combat_session(self, request: ArenaCombatRequestDTO) -> None:
        await self.events.publish(
            self.COMBAT_SESSION_REQUESTED,
            request.model_dump(mode="json"),
            correlation_id=request.arena_session_id,
        )
        logger.info(
            "Arena requested combat session: arena_session_id={} battle_type={} mode={}",
            request.arena_session_id,
            request.battle_type,
            request.mode,
        )

    async def enter_combat(self, char_id: int, combat_id: str) -> None:
        if hasattr(self.character_sessions, "set_combat_session"):
            await self.character_sessions.set_combat_session(char_id, combat_id)
        if hasattr(self.character_sessions, "set_state"):
            await self.character_sessions.set_state(char_id, CoreDomain.COMBAT)

    async def leave_arena(self, char_id: int) -> None:
        try:
            await self.character_sessions.set_state(char_id, CoreDomain.EXPLORATION)
        except Exception:
            logger.warning("Arena leave state update skipped: char_id={}", char_id)
