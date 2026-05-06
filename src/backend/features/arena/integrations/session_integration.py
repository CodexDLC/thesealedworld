from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO

if TYPE_CHECKING:
    from src.backend.features.arena.repositories.session_store import ArenaSessionStore


class ArenaSessionIntegration:
    GS_RANGE_PERCENT = 0.15
    DEFAULT_GS = 100
    REQUEST_TTL_SEC = 300

    def __init__(self, store: ArenaSessionStore) -> None:
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
        await self.store.add_to_queue(
            ArenaQueueRequestDTO(
                char_id=char_id,
                mode=mode,
                gs=gs,
                wait_limit_sec=wait_limit_sec,
                commitment_id=commitment_id,
                commitment_ttl=commitment_ttl,
                request_id=request_id or uuid.uuid4().hex,
            )
        )
        return gs

    async def leave_queue(self, char_id: int, mode: str) -> None:
        await self.store.remove_from_queue(mode, char_id)
        await self.store.delete_request(char_id)

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
        return token if await self.store.acquire_match_lock(char_id, token) else None

    async def release_match_lock(self, char_id: int, token: str) -> None:
        await self.store.release_match_lock(char_id, token)

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
