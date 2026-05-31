import json
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis

from src.backend.chat.dto.message import ChannelType, IncomingMessageDTO, MessageTabDTO, OutgoingMessageDTO
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

    async def push_combat(self, payload: dict[str, Any]) -> None:
        """Open/update a combat chat tab and fan out a chat message to combat participants."""
        now = datetime.now(UTC)
        session_id = str(payload["scope_id"])
        tab = MessageTabDTO.model_validate(
            payload.get("tab")
            or {
                "kind": "combat",
                "key": f"combat_{session_id}",
                "title": "БОЙ",
                "open_policy": "force_open",
                "closeable": True,
                "accent": "combat",
            }
        )
        recipients = await self._resolve_recipient_topics(payload.get("recipients", []))
        topic = f"chat:combat:{session_id}"
        for cid in recipients:
            self._manager.subscribe_user(cid, topic)

        outgoing = OutgoingMessageDTO.build(
            channel="combat",
            scope_id=session_id,
            sender_id=uuid.UUID(str(payload.get("sender_id"))) if payload.get("sender_id") else uuid.UUID(int=0),
            sender_name=payload.get("sender_name", "Combat"),
            content=payload.get("content", ""),
            created_at=now,
            tab=tab,
            presentation=payload.get("presentation") or {"render": "chat_text"},
            meta=payload.get("meta"),
        )
        await self.push_outgoing(outgoing.model_dump(mode="json"), topic=topic)

    async def _resolve_recipient_topics(self, recipients: list[Any]) -> list[str]:
        resolved: list[str] = []
        seen: set[str] = set()
        for raw in recipients:
            if raw is None:
                continue
            value = str(raw)
            mapped = await self._redis.get(f"chat:char_to_user:{value}")
            topic_id = str(mapped or value)
            if topic_id in seen:
                continue
            seen.add(topic_id)
            resolved.append(topic_id)
        return resolved
