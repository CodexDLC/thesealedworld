import json
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis

from src.backend.chat.dto.message import ChannelType, IncomingMessageDTO, OutgoingMessageDTO
from src.backend.chat.services.connection_manager import ChatConnectionManager
from src.backend.config.settings import settings


def _topic(channel: ChannelType, scope_id: str | None) -> str:
    if scope_id:
        return f"chat:{channel}:{scope_id}"
    return f"chat:{channel}"


class MessageService:
    def __init__(self, manager: ChatConnectionManager, redis: aioredis.Redis) -> None:
        self._manager = manager
        self._redis = redis

    async def handle_incoming(
        self,
        msg: IncomingMessageDTO,
        sender_id: uuid.UUID,
        sender_name: str,
    ) -> None:
        now = datetime.now(UTC)
        outgoing = OutgoingMessageDTO.build(
            channel=msg.channel,
            scope_id=msg.scope_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=msg.content,
            created_at=now,
        )
        topic = _topic(msg.channel, msg.scope_id)
        payload = outgoing.model_dump(mode="json")

        # 1. Fan-out to connected clients (in-memory, no broker)
        await self._manager.broadcast_topic(topic, payload)

        # 2. Buffer to Redis Stream for archiver
        stream_key = f"chat:buffer:{topic}"
        await self._redis.xadd(
            stream_key,
            {"data": json.dumps(payload)},
            maxlen=settings.chat_buffer_maxlen,
            approximate=True,
        )

    async def push_outgoing(self, payload: dict[str, Any], *, topic: str | None = None) -> None:
        channel = payload.get("channel", "system")
        scope_id = payload.get("scope_id")
        resolved_topic = topic or _topic(channel, scope_id)
        await self._manager.broadcast_topic(resolved_topic, payload)
        stream_key = f"chat:buffer:{resolved_topic}"
        await self._redis.xadd(
            stream_key,
            {"data": json.dumps(payload)},
            maxlen=settings.chat_buffer_maxlen,
            approximate=True,
        )

    async def push_system(
        self,
        character_id: str,
        content: str,
    ) -> None:
        """Push a server-generated system message to a specific player."""
        now = datetime.now(UTC)
        payload = {
            "id": str(uuid.uuid4()),
            "channel": "system",
            "scope_id": character_id,
            "sender_id": "system",
            "sender_name": "System",
            "content": content,
            "created_at": now.isoformat(),
        }
        await self.push_outgoing(payload)
