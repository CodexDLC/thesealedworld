from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import ASCENDING, ReturnDocument

COMBAT_DOCUMENTS_COLLECTION = "combat_documents"


class CombatDocumentRepository:
    """Mongo repository for full combat analytics documents."""

    def __init__(self, database: Any) -> None:
        self.database = database
        self.collection = database[COMBAT_DOCUMENTS_COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index([("combat_id", ASCENDING)], unique=True)
        await self.collection.create_index([("finished_at", ASCENDING)])
        await self.collection.create_index([("battle_type", ASCENDING), ("finished_at", ASCENDING)])
        await self.collection.create_index([("location_id", ASCENDING), ("finished_at", ASCENDING)])
        await self.collection.create_index([("winner_team", ASCENDING), ("finished_at", ASCENDING)])

    async def upsert(self, document: dict[str, Any]) -> dict[str, Any]:
        combat_id = str(document["combat_id"])
        await self.ensure_indexes()
        stored = await self.collection.find_one_and_update(
            {"combat_id": combat_id},
            {"$set": {**document, "combat_id": combat_id}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return dict(stored or document)

    async def get_by_combat_id(self, combat_id: str) -> dict[str, Any] | None:
        row = await self.collection.find_one({"combat_id": str(combat_id)})
        return dict(row) if isinstance(row, dict) else None

    async def query_for_rollups(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        battle_type: str | None = None,
        location_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if start is not None or end is not None:
            finished_at: dict[str, Any] = {}
            if start is not None:
                finished_at["$gte"] = start
            if end is not None:
                finished_at["$lt"] = end
            query["finished_at"] = finished_at
        if battle_type:
            query["battle_type"] = str(battle_type)
        if location_id:
            query["location_id"] = str(location_id)
        cursor = self.collection.find(query).sort("finished_at", ASCENDING).limit(int(limit))
        return [dict(row) async for row in cursor]
