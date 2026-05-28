from __future__ import annotations

from typing import Any


class CombatAnnouncementManager:
    ANNOUNCEMENT_TTL_SECONDS = 86400

    def __init__(self, redis: Any) -> None:
        self.redis = redis

    def build_claim_key(self, session_id: str, kind: str) -> str:
        return f"combat:announcement:{session_id}:{kind}"

    async def claim_once(self, session_id: str, kind: str) -> bool:
        return bool(
            await self.redis.set(
                self.build_claim_key(session_id, kind),
                "1",
                nx=True,
                ex=self.ANNOUNCEMENT_TTL_SECONDS,
            )
        )
