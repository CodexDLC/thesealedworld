from __future__ import annotations

import json
from typing import TYPE_CHECKING

from loguru import logger

from src.backend.features.arena.integrations.arena_integration import ArenaIntegration
from src.backend.features.arena.integrations.session_integration import ArenaSessionIntegration
from src.backend.features.arena.integrations.stream_client import ArenaStreamClient
from src.backend.features.character.events import CharacterEvents
from src.backend.infrastructure.actor_commitments import ActorCommitmentManager
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.arena.dto.session import ArenaCombatRequestDTO
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager


class ArenaSystemIntegrator:
    COMBAT_SESSION_REQUESTED = "combat.session_requested"
    COMBAT_COMMITMENTS_REQUESTED = CharacterEvents.COMBAT_COMMITMENTS_REQUESTED
    COMMITMENT_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        *,
        events: GameEventProducer,
        character_sessions: CharacterSessionManager,
    ) -> None:
        self.events = events
        self.character_sessions = character_sessions

    async def request_combat_session(self, request: ArenaCombatRequestDTO) -> None:
        await self.events.publish(
            self.COMBAT_SESSION_REQUESTED,
            request.model_dump(mode="json"),
            correlation_id=request.arena_session_id,
        )
        logger.bind(
            arena_session_id=request.arena_session_id,
            battle_type=request.battle_type,
            mode=request.mode,
        ).info("ArenaCombatSessionRequested")

    async def create_combat_commitment(self, *, request_id: str, char_id: int, ttl: int) -> str | None:
        response = await self.events.request(
            self.COMBAT_COMMITMENTS_REQUESTED,
            {
                "player_ids": json.dumps([char_id]),
                "monster_ids": "[]",
                "ttl": ttl,
                "include": json.dumps(["combat", "status", "runtime", "source"]),
            },
            timeout=self.COMMITMENT_TIMEOUT_SECONDS,
        )
        if not isinstance(response, dict) or response.get("status") not in ("ok", "partial"):
            logger.bind(request_id=request_id, char_id=char_id).warning("ArenaCombatCommitmentRequestFailed")
            return None
        commitments = response.get("commitments") or {}
        if isinstance(commitments, str):
            commitments = json.loads(commitments)
        if not isinstance(commitments, dict):
            return None
        source_ref = ActorCommitmentManager.source_ref("player", char_id)
        commitment = commitments.get(source_ref)
        return str(commitment) if commitment else None

    async def enter_combat(self, char_id: int, combat_id: str) -> None:
        if hasattr(self.character_sessions, "set_combat_session"):
            await self.character_sessions.set_combat_session(char_id, combat_id)
        await self.set_character_state(char_id, CoreDomain.COMBAT, prev_state=CoreDomain.ARENA)

    async def enter_arena(self, char_id: int) -> None:
        await self.set_character_state(char_id, CoreDomain.ARENA)

    async def leave_arena(self, char_id: int) -> None:
        if hasattr(self.character_sessions, "clear_arena_session"):
            await self.character_sessions.clear_arena_session(char_id)
        await self.set_character_state(char_id, CoreDomain.EXPLORATION, prev_state=CoreDomain.ARENA)

    async def attach_arena_session(self, char_id: int, arena_id: str) -> None:
        if hasattr(self.character_sessions, "set_arena_session"):
            await self.character_sessions.set_arena_session(char_id, arena_id)

    async def clear_arena_session(self, char_id: int) -> None:
        if hasattr(self.character_sessions, "clear_arena_session"):
            await self.character_sessions.clear_arena_session(char_id)

    async def resolve_arena_session_id(self, char_id: int) -> str | None:
        if not hasattr(self.character_sessions, "get_session"):
            return None
        session = await self.character_sessions.get_session(char_id)
        arena_id = ((session or {}).get("sessions") or {}).get("arena_id") if isinstance(session, dict) else None
        return str(arena_id) if arena_id else None

    async def is_combat_session_active(self, char_id: int, combat_id: str | None) -> bool:
        if not combat_id or not hasattr(self.character_sessions, "get_session"):
            return False
        session = await self.character_sessions.get_session(char_id)
        raw_sessions = (session or {}).get("sessions") if isinstance(session, dict) else None
        sessions = raw_sessions if isinstance(raw_sessions, dict) else {}
        active_id = sessions.get("combat_id") or sessions.get("combat_finalization_id")
        return str(active_id) == str(combat_id) if active_id else False

    async def set_character_state(
        self,
        char_id: int,
        state: CoreDomain,
        *,
        prev_state: CoreDomain | str | None = None,
    ) -> None:
        try:
            await self.character_sessions.set_state(char_id, state, prev_state=prev_state)
        except Exception:
            logger.bind(char_id=char_id, state=state.value).warning("ArenaRuntimeStateUpdateSkipped")


__all__ = ["ArenaIntegration", "ArenaSessionIntegration", "ArenaStreamClient", "ArenaSystemIntegrator"]
