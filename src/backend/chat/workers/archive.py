"""ARQ cron worker - archives Redis Stream chat buffers to PG indexes and Mongo buckets."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from arq import cron
from arq.connections import RedisSettings
from loguru import logger as log

from src.backend.chat.repositories.message_repo import ChatThreadRepository
from src.backend.config.settings import settings
from src.backend.core.database import get_session_context
from src.backend.infrastructure.mongo import ChatBucketRepository, get_mongo_provider

_CURSOR_KEY = "chat:archive:cursor:{stream}"
_BATCH_SIZE = 500


async def archive_chat_buffers(ctx: dict) -> None:
    """Read pending chat buffer streams and store durable Mongo-backed history."""
    redis: aioredis.Redis = ctx["redis"]
    stream_keys = await _discover_streams(redis)
    if not stream_keys:
        return

    mongo_repo = ChatBucketRepository(get_mongo_provider().database())
    archived_count = 0
    failed_count = 0

    for stream_key in stream_keys:
        cursor_field = _CURSOR_KEY.format(stream=stream_key)
        last_id: str = await redis.get(cursor_field) or "0-0"
        entries = await redis.xread({stream_key: last_id}, count=_BATCH_SIZE)
        if not entries:
            continue

        new_last_id = last_id
        for _stream, records in entries:
            for entry_id, fields in records:
                new_last_id = entry_id
                try:
                    payload = json.loads(fields.get("data", "{}"))
                    if not isinstance(payload, dict):
                        continue
                    status = await _archive_payload(payload, mongo_repo=mongo_repo)
                    if status == "stored":
                        archived_count += 1
                    else:
                        failed_count += 1
                except Exception:
                    failed_count += 1
                    log.bind(entry_id=entry_id).exception("ChatBufferEntryArchiveFailed")

        await redis.set(cursor_field, new_last_id)

    if archived_count or failed_count:
        log.bind(archived_count=archived_count, failed_count=failed_count).info("ChatMessagesArchived")


async def _archive_payload(payload: dict[str, Any], *, mongo_repo: ChatBucketRepository) -> str:
    channel = str(payload.get("channel") or "global")
    thread_type = _thread_type(channel)
    scope_id = _scope_id(payload, thread_type=thread_type)
    created_at = _parse_dt(payload.get("created_at"))
    message_id = _uuid_or_new(payload.get("id"))
    sender_id = _sender_uuid(payload.get("sender_id"))
    member_ids = _member_ids(payload, sender_id=sender_id, thread_type=thread_type)

    async with get_session_context() as session:
        repo = ChatThreadRepository(session)
        thread = await repo.get_or_create_thread(
            thread_type=thread_type,
            scope_id=scope_id,
            member_ids=member_ids,
            metadata={"source_channel": channel} if channel != thread_type else None,
        )
        try:
            bucket = await mongo_repo.append_message(
                thread_id=str(thread.id),
                thread_type=thread_type,
                scope_id=scope_id,
                created_at=created_at,
                message=_mongo_message(payload, message_id=message_id, sender_id=sender_id, created_at=created_at),
            )
            await repo.add_message_index(
                message_id=message_id,
                thread_id=thread.id,
                sender_id=sender_id,
                created_at=created_at,
                mongo_collection=bucket.collection,
                mongo_bucket_id=bucket.bucket_id,
                bucket_seq=bucket.seq,
                mongo_status="stored",
            )
            return "stored"
        except Exception:
            await repo.add_message_index(
                message_id=message_id,
                thread_id=thread.id,
                sender_id=sender_id,
                created_at=created_at,
                mongo_collection=None,
                mongo_bucket_id=None,
                bucket_seq=None,
                mongo_status="write_failed",
            )
            log.bind(message_id=str(message_id), thread_id=str(thread.id)).exception("ChatMongoBucketWriteFailed")
            return "write_failed"


async def _discover_streams(redis: aioredis.Redis) -> list[str]:
    stream_keys: list[str] = []
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor, match="chat:buffer:*", count=200)
        stream_keys.extend(k for k in keys if isinstance(k, str))
        if cursor == 0:
            break
    return stream_keys


def _mongo_message(
    payload: dict[str, Any],
    *,
    message_id: uuid.UUID,
    sender_id: uuid.UUID,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "id": str(message_id),
        "sender_id": str(sender_id),
        "t": created_at,
        "content": str(payload.get("content") or ""),
        "template": payload.get("template"),
        "variables": payload.get("variables") or {},
        "result": payload.get("result") or {},
        "presentation": payload.get("presentation") or {},
        "meta": {**(payload.get("meta") or {}), "sender_name": str(payload.get("sender_name") or "")},
    }


def _thread_type(channel: str) -> str:
    if channel == "zone":
        return "location"
    if channel in {"global", "trade"}:
        return "world"
    if channel in {"dm", "system", "combat", "party"}:
        return channel
    return "world"


def _scope_id(payload: dict[str, Any], *, thread_type: str) -> str | None:
    scope = payload.get("scope_id")
    if scope:
        return str(scope)
    if thread_type == "world":
        return str(payload.get("channel") or "global")
    return None


def _member_ids(payload: dict[str, Any], *, sender_id: uuid.UUID, thread_type: str) -> list[uuid.UUID] | None:
    ids: list[uuid.UUID] = []
    for value in payload.get("recipients") or []:
        parsed = _optional_uuid(value)
        if parsed:
            ids.append(parsed)
    if thread_type in {"dm", "system", "combat", "party"} and sender_id.int != 0:
        ids.append(sender_id)
    return list(dict.fromkeys(ids)) or None


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except Exception:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _uuid_or_new(value: Any) -> uuid.UUID:
    parsed = _optional_uuid(value)
    return parsed or uuid.uuid4()


def _sender_uuid(value: Any) -> uuid.UUID:
    if value == "system":
        return uuid.UUID(int=0)
    return _uuid_or_new(value)


def _optional_uuid(value: Any) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


async def startup(ctx: dict) -> None:
    ctx["redis"] = aioredis.from_url(settings.effective_redis_url, decode_responses=True)


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
