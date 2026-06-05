from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING

from src.backend.infrastructure.mongo import get_mongo_provider

GENERATED_MONSTER_ACTORS_COLLECTION = "generated_monster_actors"
GENERATED_MONSTER_ACTOR_KIND = "monster_actor_projection"
GENERATED_MONSTER_ACTOR_SCHEMA_VERSION = 1
GENERATED_MONSTER_ACTOR_SNAPSHOT_VERSION = 1


class GeneratedMonsterActorDocumentError(ValueError):
    pass


class MissingGeneratedMonsterActorDocumentError(GeneratedMonsterActorDocumentError):
    pass


class MissingGeneratedMonsterTierSnapshotError(GeneratedMonsterActorDocumentError):
    pass


class UnsupportedGeneratedMonsterActorSchemaError(GeneratedMonsterActorDocumentError):
    pass


MissingGeneratedMonsterActorDocument = MissingGeneratedMonsterActorDocumentError
MissingGeneratedMonsterTierSnapshot = MissingGeneratedMonsterTierSnapshotError


class GeneratedMonsterActorRepository:
    """Mongo repository for generated monster actor documents and tier snapshots."""

    def __init__(self, database: Any | None = None) -> None:
        self.database = database
        self.collection = (database if database is not None else get_mongo_provider().database())[
            GENERATED_MONSTER_ACTORS_COLLECTION
        ]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [
                ("document_kind", ASCENDING),
                ("clan_id", ASCENDING),
                ("variant_id", ASCENDING),
                ("member_hash", ASCENDING),
            ],
            unique=True,
            name="uq_generated_monster_actor_identity",
        )
        await self.collection.create_index([("member_id", ASCENDING)], name="ix_generated_monster_actor_member")
        await self.collection.create_index(
            [("mongo_actor_key", ASCENDING)], unique=True, name="uq_generated_monster_actor_key"
        )
        await self.collection.create_index(
            [("family_id", ASCENDING), ("variant_id", ASCENDING), ("resource_version", ASCENDING)],
            name="ix_generated_monster_actor_resource",
        )

    async def upsert_actor_document(self, document: dict[str, Any]) -> str:
        normalized = self._normalize_document(document)
        await self.ensure_indexes()
        now = datetime.now(UTC)
        normalized["updated_at"] = now
        await self.collection.update_one(
            {"_id": normalized["_id"]},
            {"$set": normalized, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return str(normalized["_id"])

    async def fetch_actor_documents_by_keys(self, actor_keys: Sequence[str]) -> dict[str, dict[str, Any]]:
        keys = [str(key) for key in actor_keys if str(key)]
        if not keys:
            return {}
        cursor = self.collection.find({"mongo_actor_key": {"$in": keys}})
        result: dict[str, dict[str, Any]] = {}
        async for document in cursor:
            normalized = self._validate_document(document)
            result[str(normalized["mongo_actor_key"])] = normalized
        return result

    async def require_actor_document(self, mongo_actor_key: str) -> dict[str, Any]:
        document = await self.collection.find_one({"mongo_actor_key": str(mongo_actor_key)})
        if not isinstance(document, dict):
            raise MissingGeneratedMonsterActorDocumentError(
                f"Missing generated monster actor document: {mongo_actor_key}"
            )
        return self._validate_document(document)

    async def require_tier_snapshot(self, mongo_actor_key: str, effective_tier: int) -> dict[str, Any]:
        document = await self.require_actor_document(mongo_actor_key)
        snapshots = document.get("tier_snapshots")
        if not isinstance(snapshots, dict):
            raise MissingGeneratedMonsterTierSnapshotError(
                f"Missing tier_snapshots for generated monster actor: {mongo_actor_key}"
            )
        key = _tier_key(effective_tier)
        snapshot = snapshots.get(key)
        if not isinstance(snapshot, dict):
            raise MissingGeneratedMonsterTierSnapshotError(
                f"Missing generated monster tier snapshot actor={mongo_actor_key} effective_tier={key}"
            )
        return dict(snapshot)

    @staticmethod
    def actor_key(*, clan_id: str, variant_id: str, member_hash: str) -> str:
        return f"actor:{clan_id}:{variant_id}:{member_hash}"

    @classmethod
    def _normalize_document(cls, document: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(document)
        normalized["document_kind"] = GENERATED_MONSTER_ACTOR_KIND
        normalized["schema_version"] = int(normalized.get("schema_version") or GENERATED_MONSTER_ACTOR_SCHEMA_VERSION)
        normalized["snapshot_version"] = int(
            normalized.get("snapshot_version") or GENERATED_MONSTER_ACTOR_SNAPSHOT_VERSION
        )
        if normalized["schema_version"] != GENERATED_MONSTER_ACTOR_SCHEMA_VERSION:
            raise UnsupportedGeneratedMonsterActorSchemaError(
                f"Unsupported generated monster actor schema_version={normalized['schema_version']}"
            )
        for key in ("clan_id", "family_id", "variant_id", "member_id", "member_hash", "mongo_actor_key"):
            value = str(normalized.get(key) or "").strip()
            if not value:
                raise ValueError(f"Generated monster actor document requires {key}")
            normalized[key] = value
        normalized["_id"] = str(
            normalized.get("_id")
            or cls.actor_key(
                clan_id=normalized["clan_id"],
                variant_id=normalized["variant_id"],
                member_hash=normalized["member_hash"],
            )
        )
        normalized["base_projection"] = _dict(normalized.get("base_projection"))
        normalized["tier_snapshots"] = {
            _tier_key(tier): _dict(snapshot)
            for tier, snapshot in _dict(normalized.get("tier_snapshots")).items()
            if str(tier).strip()
        }
        return normalized

    @classmethod
    def _validate_document(cls, document: dict[str, Any]) -> dict[str, Any]:
        normalized = cls._normalize_document(document)
        if normalized.get("document_kind") != GENERATED_MONSTER_ACTOR_KIND:
            raise UnsupportedGeneratedMonsterActorSchemaError(
                f"Unsupported generated monster actor document_kind={normalized.get('document_kind')}"
            )
        return normalized


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _tier_key(value: Any) -> str:
    raw = str(value).strip()
    if raw.startswith("tier_"):
        raw = raw.removeprefix("tier_")
    return f"tier_{int(raw)}"


__all__ = [
    "GENERATED_MONSTER_ACTOR_KIND",
    "GENERATED_MONSTER_ACTOR_SCHEMA_VERSION",
    "GENERATED_MONSTER_ACTOR_SNAPSHOT_VERSION",
    "GENERATED_MONSTER_ACTORS_COLLECTION",
    "GeneratedMonsterActorDocumentError",
    "GeneratedMonsterActorRepository",
    "MissingGeneratedMonsterActorDocument",
    "MissingGeneratedMonsterActorDocumentError",
    "MissingGeneratedMonsterTierSnapshot",
    "MissingGeneratedMonsterTierSnapshotError",
    "UnsupportedGeneratedMonsterActorSchemaError",
]
