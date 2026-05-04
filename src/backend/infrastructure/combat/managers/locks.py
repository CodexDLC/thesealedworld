from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.infrastructure.combat.managers.session import CombatSessionManager

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class CombatLockManager:
    def __init__(self, redis: RedisService) -> None:
        self.store = CombatSessionManager(redis)

    async def acquire(self, session_id: str, owner: str, *, ttl: int = 60) -> bool:
        return await self.store.acquire_busy_lock(session_id, owner, ttl=ttl)

    async def release(self, session_id: str, owner: str) -> None:
        await self.store.release_busy_lock(session_id, owner)

    async def check_and_lock_busy_for_collector(self, session_id: str) -> bool:
        return await self.acquire(session_id, "pending", ttl=30)

    async def acquire_worker_lock(self, session_id: str, worker_id: str) -> bool:
        script = """
        local val = redis.call('GET', KEYS[1])
        if val == 'pending' or not val then
            redis.call('SET', KEYS[1], ARGV[1], 'EX', 60)
            return 1
        end
        return 0
        """
        return bool(await self.store._client().eval(script, 1, self.store.busy_lock_key(session_id), worker_id))

    async def check_worker_lock(self, session_id: str, worker_id: str) -> bool:
        return await self.store._client().get(self.store.busy_lock_key(session_id)) == worker_id

    async def release_worker_lock_safe(self, session_id: str, worker_id: str) -> None:
        await self.release(session_id, worker_id)
