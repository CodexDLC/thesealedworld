from __future__ import annotations

from typing import Any

import pytest

from src.backend.infrastructure.rift import RiftInstanceState, RiftPortalKey, RiftRunState
from src.backend.infrastructure.rift.repositories import (
    RiftInstanceStateRepository,
    RiftPortalKeyRepository,
    RiftRunStateRepository,
)


@pytest.mark.unit
async def test_instance_state_repository_upserts_and_reads_by_primary_key() -> None:
    session = _FakeAsyncSession()
    repository = RiftInstanceStateRepository(session)  # type: ignore[arg-type]
    state = RiftInstanceState(
        rift_instance_id="rift-1",
        setting_key="starter_rift",
        zones_json={},
        graph_json={},
        nodes_state_json={},
        objectives_json={},
        runtime_flags_json={},
        state_meta_json={},
    )

    merged = await repository.upsert(state)
    loaded = await repository.get("rift-1")

    assert merged is state
    assert loaded is state
    assert session.flushed is True


@pytest.mark.unit
async def test_run_state_repository_upserts_and_lists_by_instance() -> None:
    session = _FakeAsyncSession()
    repository = RiftRunStateRepository(session)  # type: ignore[arg-type]
    state = RiftRunState(
        rift_run_id="run-1",
        rift_instance_id="rift-1",
        participant_scope="solo",
        participant_ref="char:1",
        current_zone_key="z01",
        current_node_id="z01:0_0",
        visited_node_ids=["z01:0_0"],
        discovered_node_ids=["z01:0_0"],
        entry_context_json={},
        run_state_json={},
    )

    await repository.upsert(state)
    loaded = await repository.get("run-1")
    listed = await repository.list_by_instance("rift-1")

    assert loaded is state
    assert listed == [state]


@pytest.mark.unit
async def test_portal_key_repository_upserts_payload_and_marks_status() -> None:
    session = _FakeAsyncSession()
    repository = RiftPortalKeyRepository(session)  # type: ignore[arg-type]

    portal = await repository.upsert_from_payload(
        {
            "portal_id": "portal-1",
            "portal_key": "starter:7",
            "source": "scenario",
            "source_ref": "awakening_rift:knockout",
            "rift_key": "starter_rift",
            "entry_reason": "knockout",
            "entry_mode": "prepared_activation",
            "owner_type": "character",
            "owner_id": "char:7",
            "participant_scope": "solo",
            "rift_session_id": "rift:run:1",
            "rift_instance_id": "rift-1",
            "exit_policy": {"target_state": "exploration", "location_id": "52_48"},
            "entry_context": {"combat_power": {"player_gear_score": 300}},
        }
    )
    loaded = await repository.get("portal-1")
    by_session = await repository.get_by_rift_session("rift:run:1")
    marked = await repository.mark_status(
        "portal-1",
        status="completed",
        reason="heart_closed",
        details={"close_rift_on_exit": True},
    )

    assert loaded is portal
    assert by_session is portal
    assert marked is portal
    assert portal.portal_key == "starter:7"
    assert portal.exit_target_state == "exploration"
    assert portal.exit_location_id == "52_48"
    assert portal.entry_context_json["combat_power"]["player_gear_score"] == 300
    assert portal.status == "completed"
    assert portal.closed_at is not None
    assert portal.state_json["status_reason"] == "heart_closed"
    assert portal.state_json["details"]["close_rift_on_exit"] is True


class _FakeAsyncSession:
    def __init__(self) -> None:
        self.objects: dict[tuple[type[Any], str], Any] = {}
        self.flushed = False

    async def merge(self, obj: Any) -> Any:
        primary_key = (
            getattr(obj, "portal_id", None)
            or getattr(obj, "rift_run_id", None)
            or getattr(obj, "rift_instance_id", None)
        )
        self.objects[(type(obj), primary_key)] = obj
        return obj

    async def flush(self) -> None:
        self.flushed = True

    async def get(self, model: type[Any], primary_key: str) -> Any | None:
        return self.objects.get((model, primary_key))

    async def execute(self, statement: Any) -> _FakeResult:
        _ = statement
        return _FakeResult([obj for (model, _), obj in self.objects.items() if model in {RiftRunState, RiftPortalKey}])


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
