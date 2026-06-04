from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING

RIFT_SETTING_DOCUMENTS_COLLECTION = "rift_setting_documents"
RIFT_NODE_DOCUMENTS_COLLECTION = "rift_node_documents"
RIFT_SETTING_DOCUMENT_KIND = "rift_setting_document"
RIFT_NODE_DOCUMENT_KIND = "rift_node_document"
RIFT_CATALOG_DOCUMENT_SCHEMA_VERSION = 1


class RiftCatalogDocumentRepository:
    def __init__(self, database: Any) -> None:
        self.database = database
        self.setting_collection = database[RIFT_SETTING_DOCUMENTS_COLLECTION]
        self.node_collection = database[RIFT_NODE_DOCUMENTS_COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.setting_collection.create_index(
            [("document_kind", ASCENDING), ("setting_key", ASCENDING)],
            unique=True,
            name="uq_rift_setting_documents_setting",
        )
        await self.node_collection.create_index(
            [("document_kind", ASCENDING), ("pool_node_id", ASCENDING)],
            unique=True,
            name="uq_rift_node_documents_pool_node",
        )
        await self.node_collection.create_index(
            [("setting_key", ASCENDING), ("pool_node_key", ASCENDING)],
            name="ix_rift_node_documents_setting_pool_key",
        )

    async def upsert_setting_document(self, *, setting_key: str, payload: dict[str, Any]) -> str:
        now = datetime.now(UTC)
        document_id = f"rift-setting:{setting_key}"
        document = {
            "document_kind": RIFT_SETTING_DOCUMENT_KIND,
            "schema_version": RIFT_CATALOG_DOCUMENT_SCHEMA_VERSION,
            "setting_key": str(setting_key),
            **payload,
            "updated_at": now,
        }
        await self.ensure_indexes()
        await self.setting_collection.update_one(
            {"document_kind": RIFT_SETTING_DOCUMENT_KIND, "setting_key": str(setting_key)},
            {"$set": document, "$setOnInsert": {"_id": document_id, "created_at": now}},
            upsert=True,
        )
        return document_id

    async def upsert_node_document(
        self,
        *,
        pool_node_id: str,
        setting_key: str,
        pool_node_key: str,
        payload: dict[str, Any],
    ) -> str:
        now = datetime.now(UTC)
        document_id = f"rift-node:{pool_node_id}"
        document = {
            "document_kind": RIFT_NODE_DOCUMENT_KIND,
            "schema_version": RIFT_CATALOG_DOCUMENT_SCHEMA_VERSION,
            "pool_node_id": str(pool_node_id),
            "setting_key": str(setting_key),
            "pool_node_key": str(pool_node_key),
            **payload,
            "updated_at": now,
        }
        await self.ensure_indexes()
        await self.node_collection.update_one(
            {"document_kind": RIFT_NODE_DOCUMENT_KIND, "pool_node_id": str(pool_node_id)},
            {"$set": document, "$setOnInsert": {"_id": document_id, "created_at": now}},
            upsert=True,
        )
        return document_id
