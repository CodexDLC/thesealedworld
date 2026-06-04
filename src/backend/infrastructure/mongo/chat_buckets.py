from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo import ASCENDING, ReturnDocument

CHAT_BUCKET_DOCUMENT_KIND = "chat_message_bucket"
CHAT_BUCKET_SCHEMA_VERSION = 1
DEFAULT_MAX_BUCKET_MESSAGES = 1000
CHAT_BUCKET_THREAD_TYPES = ("dm", "system", "location", "combat", "world")


@dataclass(frozen=True)
class ChatBucketRef:
    collection: str
    bucket_id: str
    seq: int


class ChatBucketRepository:
    """Mongo repository for bounded chat message buckets."""

    def __init__(self, database: Any, *, max_bucket_messages: int = DEFAULT_MAX_BUCKET_MESSAGES) -> None:
        self.database = database
        self.max_bucket_messages = max(1, int(max_bucket_messages))
        self._indexed: set[str] = set()

    async def append_message(
        self,
        *,
        thread_id: str,
        thread_type: str,
        scope_id: str | None,
        created_at: datetime,
        message: dict[str, Any],
    ) -> ChatBucketRef:
        policy = _bucket_policy(thread_type)
        bucket_start = _bucket_start(created_at, policy["granularity"])
        bucket_end = bucket_start + policy["duration"]
        collection_name = policy["collection"]
        collection = self.database[collection_name]
        await self._ensure_indexes(collection_name)

        for shard_no in range(100):
            bucket_id = _bucket_id(thread_id, bucket_start, shard_no)
            current = await collection.find_one(
                {"_id": bucket_id},
                {"message_count": 1, "closed": 1},
            )
            current_count = int((current or {}).get("message_count") or 0)
            if current and (current.get("closed") or current_count >= self.max_bucket_messages):
                await collection.update_one({"_id": bucket_id}, {"$set": {"closed": True}})
                continue
            seq = current_count + 1
            message_with_seq = {**message, "seq": seq}

            stored = await collection.find_one_and_update(
                {"_id": bucket_id, "closed": {"$ne": True}},
                {
                    "$setOnInsert": {
                        "_id": bucket_id,
                        "document_kind": CHAT_BUCKET_DOCUMENT_KIND,
                        "schema_version": CHAT_BUCKET_SCHEMA_VERSION,
                        "thread_id": str(thread_id),
                        "thread_type": str(thread_type),
                        "scope_id": scope_id,
                        "bucket_start": bucket_start,
                        "bucket_end": bucket_end,
                        "bucket_granularity": policy["granularity"],
                        "shard_no": shard_no,
                        "closed": False,
                        "messages": [],
                    },
                    "$push": {"messages": message_with_seq},
                    "$inc": {"message_count": 1},
                    "$set": {"updated_at": datetime.now(UTC)},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            seq = int((stored or {}).get("message_count") or seq)
            if seq >= self.max_bucket_messages:
                await collection.update_one({"_id": bucket_id}, {"$set": {"closed": True}})
            return ChatBucketRef(collection=collection_name, bucket_id=bucket_id, seq=seq)

        raise RuntimeError(f"no open chat bucket for thread_id={thread_id}")

    async def get_messages(self, refs: list[tuple[str, str, int | None]]) -> dict[tuple[str, str, int], dict[str, Any]]:
        grouped: dict[tuple[str, str], set[int]] = {}
        for collection, bucket_id, seq in refs:
            if not collection or not bucket_id or seq is None:
                continue
            grouped.setdefault((collection, bucket_id), set()).add(int(seq))

        messages: dict[tuple[str, str, int], dict[str, Any]] = {}
        for (collection_name, bucket_id), seqs in grouped.items():
            doc = await self.database[collection_name].find_one({"_id": bucket_id}, {"messages": 1})
            if not isinstance(doc, dict):
                continue
            for message in doc.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                seq = int(message.get("seq") or 0)
                if seq in seqs:
                    messages[(collection_name, bucket_id, seq)] = message
        return messages

    async def ensure_indexes(self) -> None:
        for thread_type in CHAT_BUCKET_THREAD_TYPES:
            await self._ensure_indexes(_bucket_policy(thread_type)["collection"])

    async def _ensure_indexes(self, collection_name: str) -> None:
        if collection_name in self._indexed:
            return
        collection = self.database[collection_name]
        await collection.create_index([("thread_id", ASCENDING), ("bucket_start", ASCENDING), ("shard_no", ASCENDING)])
        await collection.create_index(
            [("thread_type", ASCENDING), ("scope_id", ASCENDING), ("bucket_start", ASCENDING)]
        )
        await collection.create_index([("closed", ASCENDING), ("message_count", ASCENDING)])
        self._indexed.add(collection_name)


def _bucket_policy(thread_type: str) -> dict[str, Any]:
    normalized = str(thread_type or "global")
    if normalized == "dm":
        return {"collection": "chat_private_buckets", "granularity": "day", "duration": timedelta(days=1)}
    if normalized == "system":
        return {"collection": "chat_system_buckets", "granularity": "day", "duration": timedelta(days=1)}
    if normalized == "location":
        return {"collection": "chat_location_buckets", "granularity": "15m", "duration": timedelta(minutes=15)}
    if normalized == "combat":
        return {"collection": "chat_combat_buckets", "granularity": "combat", "duration": timedelta(days=3650)}
    return {"collection": "chat_world_buckets", "granularity": "5m", "duration": timedelta(minutes=5)}


def _bucket_start(value: datetime, granularity: str) -> datetime:
    dt = value if value.tzinfo else value.replace(tzinfo=UTC)
    dt = dt.astimezone(UTC)
    if granularity == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "15m":
        minute = dt.minute - (dt.minute % 15)
        return dt.replace(minute=minute, second=0, microsecond=0)
    if granularity == "5m":
        minute = dt.minute - (dt.minute % 5)
        return dt.replace(minute=minute, second=0, microsecond=0)
    return dt.replace(second=0, microsecond=0)


def _bucket_id(thread_id: str, bucket_start: datetime, shard_no: int) -> str:
    return f"chat-bucket:{thread_id}:{bucket_start.isoformat()}:{shard_no}"
