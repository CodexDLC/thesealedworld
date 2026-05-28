from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO, ArenaRuntimeSessionDTO
from src.shared.schemas.arena import ArenaScreenEnum

if TYPE_CHECKING:
    from src.backend.infrastructure.arena.managers import ArenaSessionManager


class ArenaSessionIntegration:
    GS_RANGE_PERCENT = 0.15
    DEFAULT_GS = 100
    REQUEST_TTL_SEC = 300

    def __init__(
        self,
        store: ArenaSessionManager[ArenaQueueRequestDTO, ArenaCombatRequestDTO, ArenaRuntimeSessionDTO],
    ) -> None:
        self.store = store

    async def join_queue(
        self,
        char_id: int,
        mode: str,
        *,
        wait_limit_sec: int = 60,
        request_id: str | None = None,
        commitment_id: str | None = None,
        commitment_ttl: int | None = None,
    ) -> int:
        gs = await self.get_gear_score(char_id)
        request = ArenaQueueRequestDTO(
            char_id=char_id,
            mode=mode,
            gs=gs,
            wait_limit_sec=wait_limit_sec,
            commitment_id=commitment_id,
            commitment_ttl=commitment_ttl,
            request_id=request_id or uuid.uuid4().hex,
        )
        await self.store.add_to_queue(mode, request, mode_size=request.mode_size)
        return gs

    async def create_runtime_session(self, char_id: int) -> ArenaRuntimeSessionDTO:
        session = ArenaRuntimeSessionDTO(char_id=char_id)
        await self.store.create_runtime_session(session)
        return session

    async def get_runtime_session(self, arena_id: str) -> ArenaRuntimeSessionDTO | None:
        return await self.store.get_runtime_session(arena_id)

    async def save_runtime_session(self, session: ArenaRuntimeSessionDTO) -> ArenaRuntimeSessionDTO:
        session.updated_at = time.time()
        await self.store.update_runtime_session(session)
        return session

    async def delete_runtime_session(self, arena_id: str) -> None:
        await self.store.delete_runtime_session(arena_id)

    async def set_runtime_screen(
        self,
        session: ArenaRuntimeSessionDTO,
        screen: ArenaScreenEnum,
        *,
        mode: str | None = None,
        queue_request_id: str | None = None,
        active_match_id: str | None = None,
        combat_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ArenaRuntimeSessionDTO:
        session.screen = screen
        if mode is not None or screen == ArenaScreenEnum.MAIN_MENU:
            session.mode = mode
        if queue_request_id is not None:
            session.queue_request_id = queue_request_id or None
        if active_match_id is not None:
            session.active_match_id = active_match_id or None
        if combat_id is not None:
            session.combat_id = combat_id or None
        if screen == ArenaScreenEnum.MAIN_MENU:
            session.queue_request_id = None
            session.active_match_id = None
            session.combat_id = None
            session.metadata = {}
        if metadata:
            session.metadata = {**session.metadata, **metadata}
        return await self.save_runtime_session(session)

    async def leave_queue(self, char_id: int, mode: str) -> None:
        await self.store.remove_from_queue(mode, char_id)
        await self.store.delete_request(char_id)

    async def queue_waiting_count(self, mode: str, *, exclude_char_id: int | None = None) -> int:
        count = await self.store.queue_waiting_count(mode)
        if exclude_char_id is not None and await self.store.get_request(exclude_char_id) is not None:
            return max(0, count - 1)
        return count

    async def get_request_meta(self, char_id: int) -> ArenaQueueRequestDTO | None:
        return await self.store.get_request(char_id)

    async def find_opponent(self, char_id: int, mode: str) -> int | None:
        request = await self.get_request_meta(char_id)
        if request is None:
            return None

        min_gs = request.gs * (1 - self.GS_RANGE_PERCENT)
        max_gs = request.gs * (1 + self.GS_RANGE_PERCENT)
        return await self.store.claim_opponent(mode, char_id, min_gs, max_gs)

    async def acquire_match_lock(self, char_id: int) -> str | None:
        token = uuid.uuid4().hex
        return token if await self.store.acquire_match_lock("match", char_id, token) else None

    async def release_match_lock(self, char_id: int, token: str) -> None:
        await self.store.release_match_lock("match", char_id, token)

    async def prepare_match(self, char_id: int, opponent_id: int | None, mode: str) -> None:
        await self.leave_queue(char_id, mode)
        if opponent_id is not None:
            await self.store.delete_request(opponent_id)

    async def create_match(self, match: ArenaCombatRequestDTO) -> None:
        await self.store.create_match(match)

    async def update_match(self, match: ArenaCombatRequestDTO) -> None:
        await self.store.update_match(match)

    async def get_match(self, arena_session_id: str) -> ArenaCombatRequestDTO | None:
        return await self.store.get_match(arena_session_id)

    async def get_match_for_char(self, char_id: int) -> ArenaCombatRequestDTO | None:
        return await self.store.get_match_for_char(char_id)

    async def delete_match(self, match: ArenaCombatRequestDTO) -> None:
        await self.store.delete_match(match)

    async def get_gear_score(self, char_id: int) -> int:
        _ = char_id
        return self.DEFAULT_GS
