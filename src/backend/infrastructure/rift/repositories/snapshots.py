from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING

RIFT_RUNTIME_SNAPSHOTS_COLLECTION = "rift_runtime_snapshots"
RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND = "rift_runtime_snapshot"
RIFT_RUNTIME_SNAPSHOT_SCHEMA_VERSION = 1


class UnsupportedRiftSnapshotSchemaError(RuntimeError):
    pass


class RiftRuntimeSnapshotRepository:
    def __init__(self, database: Any) -> None:
        self.database = database
        self.collection = database[RIFT_RUNTIME_SNAPSHOTS_COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("document_kind", ASCENDING), ("rift_instance_id", ASCENDING)],
            unique=True,
            name="uq_rift_runtime_snapshots_instance",
        )
        await self.collection.create_index([("rift_instance_id", ASCENDING)], name="ix_rift_runtime_snapshots_instance")
        await self.collection.create_index([("updated_at", ASCENDING)], name="ix_rift_runtime_snapshots_updated")

    async def upsert_snapshot(
        self,
        *,
        rift_instance_id: str,
        snapshot_version: int,
        instance: dict[str, Any],
        sessions: dict[str, dict[str, Any]],
        presence: dict[str, Any],
    ) -> str:
        now = datetime.now(UTC)
        document_id = f"rift-runtime-snapshot:{rift_instance_id}"
        filter_query = {
            "document_kind": RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND,
            "rift_instance_id": str(rift_instance_id),
        }
        document = {
            "document_kind": RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND,
            "schema_version": RIFT_RUNTIME_SNAPSHOT_SCHEMA_VERSION,
            "rift_instance_id": str(rift_instance_id),
            "snapshot_version": int(snapshot_version),
            "captured_at": now,
            "instance": dict(instance),
            "sessions": {str(key): dict(value) for key, value in sessions.items()},
            "presence": dict(presence),
            "updated_at": now,
        }
        await self.ensure_indexes()
        await self.collection.update_one(
            filter_query,
            {
                "$set": document,
                "$setOnInsert": {"_id": document_id, "created_at": now},
            },
            upsert=True,
        )
        stored = await self.collection.find_one(filter_query, {"_id": 1})
        if isinstance(stored, dict) and stored.get("_id") is not None:
            return str(stored["_id"])
        return document_id

    async def get_snapshot(self, rift_instance_id: str) -> dict[str, Any] | None:
        document = await self.collection.find_one(
            {
                "document_kind": RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND,
                "rift_instance_id": str(rift_instance_id),
            }
        )
        if not isinstance(document, dict):
            return None
        schema_version = int(document.get("schema_version") or 0)
        if schema_version != RIFT_RUNTIME_SNAPSHOT_SCHEMA_VERSION:
            raise UnsupportedRiftSnapshotSchemaError(
                f"Unsupported rift runtime snapshot schema_version={schema_version} "
                f"for rift_instance_id={rift_instance_id}"
            )
        return dict(document)
