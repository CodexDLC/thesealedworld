from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class TelegramMessageStore:
    """Stores Telegram message bindings for published entities."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    async def get(self, *, scope: str, entity_id: str) -> dict[str, str]:
        data = await self.redis.hgetall(self._key(scope, entity_id))
        return {str(key): str(value) for key, value in data.items()}

    async def save(
        self,
        *,
        scope: str,
        entity_id: str,
        chat_id: str,
        message_id: str,
        slug: str = "",
        kind: str = "message",
    ) -> None:
        now = datetime.now(UTC).isoformat()
        await self.redis.hset(
            name=self._key(scope, entity_id),
            mapping={
                "scope": scope,
                "entity_id": entity_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "slug": slug,
                "kind": kind,
                "created_at": now,
                "updated_at": now,
            },
        )

    async def delete(self, *, scope: str, entity_id: str) -> None:
        await self.redis.delete(self._key(scope, entity_id))

    @staticmethod
    def _key(scope: str, entity_id: str) -> str:
        return f"tg:messages:{scope}:{entity_id}"
