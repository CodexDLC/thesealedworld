"""ARQ cron worker — archives Redis Stream chat buffers to Postgres every 10-15 min."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from arq import cron
from arq.connections import RedisSettings

from src.chat.config import settings
from src.chat.core.database import get_session_context
from src.chat.models.message import ChatMessage
from src.chat.models.session import ChatSessionMessage
from src.chat.repositories.message_repo import ChatMessageRepository
from src.chat.repositories.session_repo import ChatSessionRepository

log = logging.getLogger(__name__)

_CURSOR_KEY = "chat:archive:cursor:{stream}"
_BATCH_SIZE = 500


async def archive_chat_buffers(ctx: dict) -> None:
    """Read all pending chat buffer streams and bulk-insert into Postgres."""
    redis: aioredis.Redis = ctx["redis"]

    # Discover all active buffer streams
    stream_keys: list[str] = []
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="chat:buffer:*", count=200)
        stream_keys.extend(k for k in keys if isinstance(k, str))
        if cursor == 0:
            break

    if not stream_keys:
        return

    channel_messages: list[ChatMessage] = []
    dm_messages: list[ChatSessionMessage] = []

    for stream_key in stream_keys:
        cursor_field = _CURSOR_KEY.format(stream=stream_key)
        last_id: str = await redis.get(cursor_field) or "0-0"

        entries = await redis.xread({stream_key: last_id}, count=_BATCH_SIZE)
        if not entries:
            continue

        new_last_id: str = last_id
        for _stream, records in entries:
            for entry_id, fields in records:
                new_last_id = entry_id
                try:
                    payload = json.loads(fields.get("data", "{}"))
                    channel = payload.get("channel", "global")
                    created_at = _parse_dt(payload.get("created_at"))

                    if channel == "dm":
                        session_id_raw = payload.get("scope_id")
                        if session_id_raw:
                            dm_messages.append(
                                ChatSessionMessage(
                                    id=uuid.UUID(payload["id"]) if payload.get("id") else uuid.uuid4(),
                                    session_id=uuid.UUID(session_id_raw),
                                    sender_id=uuid.UUID(payload["sender_id"])
                                    if payload.get("sender_id") != "system"
                                    else uuid.UUID(int=0),
                                    content=payload.get("content", ""),
                                    created_at=created_at,
                                )
                            )
                    else:
                        sender_id_raw = payload.get("sender_id", "")
                        channel_messages.append(
                            ChatMessage(
                                id=uuid.UUID(payload["id"]) if payload.get("id") else uuid.uuid4(),
                                channel_type=channel,
                                scope_id=payload.get("scope_id"),
                                sender_id=uuid.UUID(sender_id_raw)
                                if sender_id_raw and sender_id_raw != "system"
                                else uuid.UUID(int=0),
                                sender_name=payload.get("sender_name", ""),
                                content=payload.get("content", ""),
                                created_at=created_at,
                            )
                        )
                except Exception:
                    log.exception("Failed to parse chat buffer entry %s", entry_id)

        await redis.set(cursor_field, new_last_id)

    if channel_messages or dm_messages:
        async with get_session_context() as session:
            if channel_messages:
                repo = ChatMessageRepository(session)
                await repo.bulk_insert(channel_messages)
            if dm_messages:
                dm_repo = ChatSessionRepository(session)
                await dm_repo.bulk_insert_messages(dm_messages)

        log.info(
            "Archived %d channel messages and %d DM messages",
            len(channel_messages),
            len(dm_messages),
        )


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(UTC)


async def startup(ctx: dict) -> None:
    ctx["redis"] = aioredis.from_url(settings.redis_url, decode_responses=True)


async def shutdown(ctx: dict) -> None:
    await ctx["redis"].aclose()


class ChatArchiveWorkerSettings:
    functions = [archive_chat_buffers]
    cron_jobs = [
        cron(archive_chat_buffers, minute={0, 10, 20, 30, 40, 50}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.effective_redis_url)
    max_jobs = 1
