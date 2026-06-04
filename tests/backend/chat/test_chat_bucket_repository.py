from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest

from src.backend.infrastructure.mongo.chat_buckets import ChatBucketRepository


@pytest.mark.unit
async def test_dm_messages_use_private_day_bucket() -> None:
    database = _FakeMongoDatabase()
    repo = ChatBucketRepository(database, max_bucket_messages=10)

    ref = await repo.append_message(
        thread_id="thread-dm",
        thread_type="dm",
        scope_id="a:b",
        created_at=datetime(2026, 6, 4, 10, 30, tzinfo=UTC),
        message={"id": "msg-1", "content": "hi"},
    )

    assert ref.collection == "chat_private_buckets"
    assert ref.seq == 1
    doc = database["chat_private_buckets"].docs[ref.bucket_id]
    assert doc["bucket_granularity"] == "day"
    assert doc["message_count"] == 1
    assert doc["messages"][0]["seq"] == 1
    assert doc["messages"][0]["content"] == "hi"


@pytest.mark.unit
async def test_hot_world_bucket_closes_and_uses_next_shard() -> None:
    database = _FakeMongoDatabase()
    repo = ChatBucketRepository(database, max_bucket_messages=1)
    created_at = datetime(2026, 6, 4, 10, 3, tzinfo=UTC)

    first = await repo.append_message(
        thread_id="thread-world",
        thread_type="world",
        scope_id="global",
        created_at=created_at,
        message={"id": "msg-1"},
    )
    second = await repo.append_message(
        thread_id="thread-world",
        thread_type="world",
        scope_id="global",
        created_at=created_at,
        message={"id": "msg-2"},
    )

    assert first.collection == "chat_world_buckets"
    assert second.collection == "chat_world_buckets"
    assert first.bucket_id.endswith(":0")
    assert second.bucket_id.endswith(":1")
    assert database["chat_world_buckets"].docs[first.bucket_id]["closed"] is True
    assert database["chat_world_buckets"].docs[second.bucket_id]["messages"][0]["seq"] == 1


@pytest.mark.unit
async def test_get_messages_reads_only_requested_bucket_sequences() -> None:
    database = _FakeMongoDatabase()
    repo = ChatBucketRepository(database, max_bucket_messages=10)

    first = await repo.append_message(
        thread_id="thread-world",
        thread_type="world",
        scope_id="global",
        created_at=datetime(2026, 6, 4, 10, 3, tzinfo=UTC),
        message={"id": "msg-1"},
    )
    await repo.append_message(
        thread_id="thread-world",
        thread_type="world",
        scope_id="global",
        created_at=datetime(2026, 6, 4, 10, 4, tzinfo=UTC),
        message={"id": "msg-2"},
    )

    messages = await repo.get_messages([(first.collection, first.bucket_id, first.seq)])

    assert list(messages.values()) == [{"id": "msg-1", "seq": 1}]


class _FakeMongoDatabase(dict[str, Any]):
    def __missing__(self, key: str) -> _FakeMongoCollection:
        collection = _FakeMongoCollection()
        self[key] = collection
        return collection


class _FakeMongoCollection:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}
        self.indexes: list[Any] = []

    async def create_index(self, keys: Any, **kwargs: Any) -> None:
        self.indexes.append((keys, kwargs))

    async def find_one(self, query: dict[str, Any], projection: dict[str, Any] | None = None) -> dict[str, Any] | None:
        doc = self.docs.get(str(query.get("_id")))
        return deepcopy(doc) if doc is not None else None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        doc = self.docs.get(str(query.get("_id")))
        if doc is None:
            return
        doc.update(update.get("$set") or {})

    async def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        *,
        upsert: bool,
        return_document: Any,
    ) -> dict[str, Any] | None:
        doc_id = str(query["_id"])
        doc = self.docs.get(doc_id)
        if doc is None:
            if not upsert:
                return None
            doc = dict(update.get("$setOnInsert") or {})
            self.docs[doc_id] = doc
        if doc.get("closed") is True and query.get("closed") == {"$ne": True}:
            return None
        for key, value in (update.get("$push") or {}).items():
            doc.setdefault(key, []).append(deepcopy(value))
        for key, value in (update.get("$inc") or {}).items():
            doc[key] = int(doc.get(key) or 0) + int(value)
        doc.update(update.get("$set") or {})
        return deepcopy(doc)
