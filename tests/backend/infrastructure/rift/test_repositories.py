from __future__ import annotations

from typing import Any

import pytest

from src.backend.infrastructure.rift import RiftMembership
from src.backend.infrastructure.rift.repositories import RiftMembershipRepository
from src.backend.infrastructure.rift.repositories.snapshots import (
    RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND,
    RIFT_RUNTIME_SNAPSHOT_SCHEMA_VERSION,
    RiftRuntimeSnapshotRepository,
    UnsupportedRiftSnapshotSchemaError,
)


@pytest.mark.unit
async def test_membership_repository_upserts_and_reads_active_participant_index() -> None:
    session = _FakeAsyncSession()
    repository = RiftMembershipRepository(session)  # type: ignore[arg-type]
    membership = RiftMembership(
        rift_instance_id="rift-1",
        rift_session_id="run-1",
        participant_ref="char:1",
        setting_key="starter_rift",
        status="active",
        mongo_snapshot_id="snapshot-1",
        snapshot_version=3,
        source="scenario",
        source_ref="awakening",
        current_node_id="z01:0_0",
        active_encounter_id="combat-1",
    )

    merged = await repository.upsert(membership)
    loaded = await repository.get_by_session("run-1")
    active = await repository.get_active_for_participant("char:1")
    by_instance = await repository.list_by_instance("rift-1")
    await repository.update_snapshot_refs(
        rift_instance_id="rift-1",
        mongo_snapshot_id="snapshot-2",
        snapshot_version=4,
        participant_summaries={
            "run-1": {"current_node_id": "z01:0_1", "active_encounter_id": None},
        },
    )

    assert merged is membership
    assert loaded is membership
    assert active is membership
    assert by_instance == [membership]
    assert membership.mongo_snapshot_id == "snapshot-2"
    assert membership.snapshot_version == 4
    assert membership.current_node_id == "z01:0_1"
    assert membership.active_encounter_id is None
    assert session.flushed is True


@pytest.mark.unit
async def test_runtime_snapshot_repository_writes_one_document_per_rift_instance() -> None:
    database = _FakeMongoDatabase()
    repository = RiftRuntimeSnapshotRepository(database)

    document_id = await repository.upsert_snapshot(
        rift_instance_id="rift-1",
        snapshot_version=2,
        instance={"rift_instance_id": "rift-1", "nodes": {}},
        sessions={"run-1": {"participant_ref": "char:1", "current_node_id": "z01:0_0"}},
        presence={"nodes": {"z01:0_0": ["char:1"]}},
    )
    loaded = await repository.get_snapshot("rift-1")

    assert document_id == "rift-runtime-snapshot:rift-1"
    assert loaded is not None
    assert loaded["document_kind"] == RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND
    assert loaded["schema_version"] == RIFT_RUNTIME_SNAPSHOT_SCHEMA_VERSION
    assert loaded["rift_instance_id"] == "rift-1"
    assert loaded["snapshot_version"] == 2
    assert loaded["sessions"]["run-1"]["current_node_id"] == "z01:0_0"


@pytest.mark.unit
async def test_runtime_snapshot_repository_rejects_unknown_schema_version() -> None:
    database = _FakeMongoDatabase()
    database["rift_runtime_snapshots"].documents["rift-runtime-snapshot:rift-1"] = {
        "_id": "rift-runtime-snapshot:rift-1",
        "document_kind": RIFT_RUNTIME_SNAPSHOT_DOCUMENT_KIND,
        "schema_version": 99,
        "rift_instance_id": "rift-1",
    }
    repository = RiftRuntimeSnapshotRepository(database)

    with pytest.raises(UnsupportedRiftSnapshotSchemaError, match="schema_version=99"):
        await repository.get_snapshot("rift-1")


class _FakeAsyncSession:
    def __init__(self) -> None:
        self.objects: dict[tuple[type[Any], str], Any] = {}
        self.flushed = False

    async def merge(self, obj: Any) -> Any:
        primary_key = getattr(obj, "id", None) or getattr(obj, "rift_session_id", None)
        if getattr(obj, "id", None) is None:
            obj.id = len(self.objects) + 1
        self.objects[(type(obj), str(primary_key or obj.id))] = obj
        return obj

    async def flush(self) -> None:
        self.flushed = True

    async def get(self, model: type[Any], primary_key: str) -> Any | None:
        return self.objects.get((model, str(primary_key)))

    async def execute(self, statement: Any) -> _FakeResult:
        text = str(statement)
        values = [obj for (model, _), obj in self.objects.items() if model is RiftMembership]
        if "rift_session_id" in text:
            values = [obj for obj in values if obj.rift_session_id == "run-1"]
        elif "participant_ref" in text:
            values = [obj for obj in values if obj.participant_ref == "char:1" and obj.status == "active"]
        elif "rift_instance_id" in text:
            values = [obj for obj in values if obj.rift_instance_id == "rift-1"]
        return _FakeResult(values)


class _FakeResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self.values)


class _FakeScalars:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def all(self) -> list[Any]:
        return self.values

    def first(self) -> Any | None:
        return self.values[0] if self.values else None


class _FakeMongoDatabase(dict[str, Any]):
    def __missing__(self, key: str) -> Any:
        collection = _FakeMongoCollection()
        self[key] = collection
        return collection


class _FakeMongoCollection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.indexes: list[Any] = []

    async def create_index(self, *args: Any, **kwargs: Any) -> None:
        self.indexes.append((args, kwargs))

    async def update_one(self, filter_query: dict[str, Any], update: dict[str, Any], *, upsert: bool = False) -> None:
        _ = upsert
        doc_id = str(update.get("$setOnInsert", {}).get("_id") or filter_query["rift_instance_id"])
        current = dict(self.documents.get(doc_id) or update.get("$setOnInsert") or {})
        current.update(update.get("$set") or {})
        current.setdefault("_id", doc_id)
        self.documents[doc_id] = current

    async def find_one(self, filter_query: dict[str, Any], projection: dict[str, Any] | None = None) -> dict[str, Any] | None:
        _ = projection
        for document in self.documents.values():
            if all(document.get(key) == value for key, value in filter_query.items()):
                return dict(document)
        return None
