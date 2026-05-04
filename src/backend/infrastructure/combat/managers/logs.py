from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.combat.managers.session import CombatSessionManager

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class CombatLogManager:
    def __init__(self, redis: RedisService) -> None:
        self.store = CombatSessionManager(redis)

    async def append(self, session_id: str, entry: dict[str, Any] | str) -> None:
        await self.store.append_log(session_id, entry)

    async def fetch_logs(self, session_id: str, *, start: int = 0, stop: int = -1) -> list[str]:
        return await self.store.get_logs(session_id, start=start, stop=stop)

    async def get_logs(self, session_id: str, start: int = 0, stop: int = -1) -> list[str]:
        return await self.fetch_logs(session_id, start=start, stop=stop)
