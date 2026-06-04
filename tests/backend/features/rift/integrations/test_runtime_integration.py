from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.features.rift.integrations.runtime import RiftRuntimeNotFoundError
from src.backend.infrastructure.rift.managers import RiftInstanceNotFoundError, RiftRunSessionNotFoundError


class FakeInstanceStore:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.runtime = object()
        self.missing = False
        self.instances: dict[str, Any] = {}

    async def save_instance(self, runtime: Any) -> None:
        self.calls.append(("save_instance", runtime))
        rift_instance_id = getattr(runtime, "rift_instance_id", None)
        if rift_instance_id:
            self.instances[str(rift_instance_id)] = runtime

    async def get_instance(self, rift_instance_id: str) -> Any | None:
        self.calls.append(("get_instance", rift_instance_id))
        if self.missing:
            return None
        return self.instances.get(rift_instance_id) or self.runtime

    async def require_instance(self, rift_instance_id: str) -> Any:
        self.calls.append(("require_instance", rift_instance_id))
        if self.missing:
            raise RiftInstanceNotFoundError(f"Rift instance not found: {rift_instance_id}")
        return self.instances.get(rift_instance_id) or self.runtime

    async def patch_node_event(self, rift_instance_id: str, node_id: str, event: dict[str, Any]) -> None:
        self.calls.append(("patch_node_event", rift_instance_id, node_id, event))

    async def mark_node_cleared(self, rift_instance_id: str, node_id: str) -> None:
        self.calls.append(("mark_node_cleared", rift_instance_id, node_id))

    async def set_gate_state(self, rift_instance_id: str, gate_key: str, state: dict[str, Any]) -> None:
        self.calls.append(("set_gate_state", rift_instance_id, gate_key, state))

    async def set_heart_state(self, rift_instance_id: str, state: dict[str, Any]) -> None:
        self.calls.append(("set_heart_state", rift_instance_id, state))


class FakeSessionStore:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.missing = False
        self.session: dict[str, Any] | None = None
        self.sessions: dict[str, dict[str, Any]] = {}

    async def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_session", payload))
        self.sessions[str(payload["rift_session_id"])] = dict(payload)
        return payload

    async def save_session(
        self,
        payload: dict[str, Any],
        *,
        dirty_reason: str | None = None,
        dirty_paths: list[str] | None = None,
    ) -> None:
        self.calls.append(("save_session", payload, dirty_reason, dirty_paths))

    async def get_session(self, rift_session_id: str) -> dict[str, Any] | None:
        self.calls.append(("get_session", rift_session_id))
        return self.session or self.sessions.get(rift_session_id) or {"rift_session_id": rift_session_id}

    async def require_session(self, rift_session_id: str) -> dict[str, Any]:
        self.calls.append(("require_session", rift_session_id))
        if self.missing:
            raise RiftRunSessionNotFoundError(f"Rift run session not found: {rift_session_id}")
        return self.session or self.sessions.get(rift_session_id) or {"rift_session_id": rift_session_id}

    async def mark_dirty(self, rift_session_id: str, *, reason: str, paths: list[str]) -> None:
        self.calls.append(("mark_dirty", rift_session_id, reason, paths))

    async def clear_dirty(self, rift_session_id: str) -> None:
        self.calls.append(("clear_dirty", rift_session_id))

    async def scan_dirty(self, *, limit: int = 100) -> list[str]:
        self.calls.append(("scan_dirty", limit))
        return ["run-1"]

    async def list_by_instance(self, rift_instance_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        self.calls.append(("list_by_instance", rift_instance_id, limit))
        return [session for session in self.sessions.values() if str(session.get("rift_instance_id")) == rift_instance_id]

    async def set_position(
        self,
        rift_session_id: str,
        *,
        current_node_id: str,
        previous_node_id: str | None = None,
        heading: str | None = None,
    ) -> None:
        self.calls.append(("set_position", rift_session_id, current_node_id, previous_node_id, heading))

    async def set_visited(self, rift_session_id: str, node_ids: set[str]) -> None:
        self.calls.append(("set_visited", rift_session_id, node_ids))

    async def set_discovered(self, rift_session_id: str, node_ids: set[str]) -> None:
        self.calls.append(("set_discovered", rift_session_id, node_ids))

    async def start_travel(self, rift_session_id: str, travel: dict[str, Any]) -> None:
        self.calls.append(("start_travel", rift_session_id, travel))

    async def interrupt_travel(self, rift_session_id: str, travel: dict[str, Any]) -> None:
        self.calls.append(("interrupt_travel", rift_session_id, travel))

    async def complete_travel(self, rift_session_id: str, *, last_travel: dict[str, Any]) -> None:
        self.calls.append(("complete_travel", rift_session_id, last_travel))

    async def set_active_encounter(self, rift_session_id: str, encounter_id: str) -> None:
        self.calls.append(("set_active_encounter", rift_session_id, encounter_id))

    async def clear_active_encounter(self, rift_session_id: str) -> None:
        self.calls.append(("clear_active_encounter", rift_session_id))


class FakePresenceStore:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.nodes: dict[tuple[str, str], set[str]] = {}

    async def enter_node(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.calls.append(("enter_node", rift_instance_id, node_id, participant_ref))
        self.nodes.setdefault((rift_instance_id, node_id), set()).add(participant_ref)

    async def leave_node(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.calls.append(("leave_node", rift_instance_id, node_id, participant_ref))
        self.nodes.setdefault((rift_instance_id, node_id), set()).discard(participant_ref)

    async def move_node(
        self,
        rift_instance_id: str,
        *,
        from_node_id: str | None,
        to_node_id: str,
        participant_ref: str,
    ) -> None:
        self.calls.append(("move_node", rift_instance_id, from_node_id, to_node_id, participant_ref))

    async def get_node_occupants(self, rift_instance_id: str, node_id: str) -> set[str]:
        self.calls.append(("get_node_occupants", rift_instance_id, node_id))
        return self.nodes.get((rift_instance_id, node_id), {"player:7"})

    async def join_travel(self, rift_instance_id: str, travel_id: str, participant_ref: str) -> None:
        self.calls.append(("join_travel", rift_instance_id, travel_id, participant_ref))

    async def leave_travel(self, rift_instance_id: str, travel_id: str, participant_ref: str) -> None:
        self.calls.append(("leave_travel", rift_instance_id, travel_id, participant_ref))

    async def get_travel_participants(self, rift_instance_id: str, travel_id: str) -> set[str]:
        self.calls.append(("get_travel_participants", rift_instance_id, travel_id))
        return {"player:7"}

    async def join_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        self.calls.append(("join_encounter", rift_instance_id, encounter_id, participant_ref))

    async def leave_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        self.calls.append(("leave_encounter", rift_instance_id, encounter_id, participant_ref))

    async def get_encounter_participants(self, rift_instance_id: str, encounter_id: str) -> set[str]:
        self.calls.append(("get_encounter_participants", rift_instance_id, encounter_id))
        return {"player:7"}

    async def clear_node_presence(self, rift_instance_id: str, node_id: str) -> None:
        self.calls.append(("clear_node_presence", rift_instance_id, node_id))
        self.nodes.pop((rift_instance_id, node_id), None)

    async def clear_travel_presence(self, rift_instance_id: str, travel_id: str) -> None:
        self.calls.append(("clear_travel_presence", rift_instance_id, travel_id))

    async def clear_encounter_presence(self, rift_instance_id: str, encounter_id: str) -> None:
        self.calls.append(("clear_encounter_presence", rift_instance_id, encounter_id))


class FakeMembershipRepository:
    def __init__(self) -> None:
        self.upserts: list[Any] = []
        self.records: dict[str, Any] = {}
        self.snapshot_updates: list[dict[str, Any]] = []

    async def get_by_session(self, rift_session_id: str) -> Any | None:
        return self.records.get(rift_session_id)

    async def get_active_for_participant(self, participant_ref: str) -> Any | None:
        for record in self.records.values():
            if record.participant_ref == participant_ref and record.status in {"active", "resumable"}:
                return record
        return None

    async def list_by_instance(self, rift_instance_id: str) -> list[Any]:
        return [record for record in self.records.values() if record.rift_instance_id == rift_instance_id]

    async def upsert(self, state: Any) -> Any:
        self.upserts.append(state)
        self.records[state.rift_session_id] = state
        return state

    async def update_snapshot_refs(
        self,
        *,
        rift_instance_id: str,
        mongo_snapshot_id: str,
        snapshot_version: int,
        participant_summaries: dict[str, dict[str, Any]],
    ) -> None:
        self.snapshot_updates.append(
            {
                "rift_instance_id": rift_instance_id,
                "mongo_snapshot_id": mongo_snapshot_id,
                "snapshot_version": snapshot_version,
                "participant_summaries": participant_summaries,
            }
        )
        for record in self.records.values():
            if record.rift_instance_id != rift_instance_id:
                continue
            record.mongo_snapshot_id = mongo_snapshot_id
            record.snapshot_version = snapshot_version
            summary = participant_summaries.get(record.rift_session_id) or {}
            if "current_node_id" in summary:
                record.current_node_id = summary["current_node_id"]
            if "active_encounter_id" in summary:
                record.active_encounter_id = summary["active_encounter_id"]


class FakeMembership:
    def __init__(
        self,
        *,
        rift_instance_id: str,
        rift_session_id: str,
        participant_ref: str,
        setting_key: str = "starter_rift",
        status: str = "active",
        mongo_snapshot_id: str | None = None,
        snapshot_version: int = 0,
        current_node_id: str | None = None,
        active_encounter_id: str | None = None,
    ) -> None:
        self.rift_instance_id = rift_instance_id
        self.rift_session_id = rift_session_id
        self.participant_ref = participant_ref
        self.setting_key = setting_key
        self.status = status
        self.mongo_snapshot_id = mongo_snapshot_id
        self.snapshot_version = snapshot_version
        self.current_node_id = current_node_id
        self.active_encounter_id = active_encounter_id


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self.upserts: list[dict[str, Any]] = []
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.reads: list[str] = []

    async def upsert_snapshot(
        self,
        *,
        rift_instance_id: str,
        snapshot_version: int,
        instance: dict[str, Any],
        sessions: dict[str, dict[str, Any]],
        presence: dict[str, Any],
    ) -> str:
        document_id = f"rift-runtime-snapshot:{rift_instance_id}"
        document = {
            "_id": document_id,
            "document_kind": "rift_runtime_snapshot",
            "schema_version": 1,
            "rift_instance_id": rift_instance_id,
            "snapshot_version": snapshot_version,
            "instance": instance,
            "sessions": sessions,
            "presence": presence,
        }
        self.upserts.append(document)
        self.snapshots[rift_instance_id] = document
        return document_id

    async def get_snapshot(self, rift_instance_id: str) -> dict[str, Any] | None:
        self.reads.append(rift_instance_id)
        return self.snapshots.get(rift_instance_id)


class FakeRestoreLock:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run_once(self, rift_instance_id: str, callback: Any) -> Any:
        self.calls.append(rift_instance_id)
        return await callback()


@pytest.mark.unit
async def test_runtime_integration_is_the_service_boundary_for_rift_storage() -> None:
    instance_store = FakeInstanceStore()
    session_store = FakeSessionStore()
    presence_store = FakePresenceStore()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=presence_store,
    )

    await integration.save_instance(instance_store.runtime)
    assert await integration.require_instance("rift-1") is instance_store.runtime
    await integration.patch_node_event("rift-1", "z01:1_1", {"kind": "trap"})
    await integration.mark_node_cleared("rift-1", "z01:1_1")
    await integration.set_gate_state("rift-1", "gate-1", {"state": "open"})
    await integration.set_heart_state("rift-1", {"state": "stable"})

    await integration.create_run_session({"rift_session_id": "session-1"})
    await integration.save_run_session({"rift_session_id": "session-1"})
    assert await integration.get_run_session("session-1") == {"rift_session_id": "session-1"}
    assert await integration.require_run_session("session-1") == {"rift_session_id": "session-1"}
    await integration.set_run_position("session-1", current_node_id="z01:1_1", previous_node_id="z01:1_0", heading="east")
    await integration.set_run_visited("session-1", {"z01:1_1"})
    await integration.set_run_discovered("session-1", {"z01:1_1", "z01:1_2"})
    await integration.start_run_travel("session-1", {"travel_id": "travel-1"})
    await integration.interrupt_run_travel("session-1", {"travel_id": "travel-1"})
    await integration.complete_run_travel("session-1", last_travel={"travel_id": "travel-1"})
    await integration.set_run_active_encounter("session-1", "encounter-1")
    await integration.clear_run_active_encounter("session-1")

    await integration.enter_node_presence("rift-1", "z01:1_1", "player:7")
    await integration.leave_node_presence("rift-1", "z01:1_1", "player:7")
    await integration.move_presence("rift-1", from_node_id="z01:1_1", to_node_id="z01:1_2", participant_ref="player:7")
    assert await integration.get_node_occupants("rift-1", "z01:1_2") == {"player:7"}
    await integration.join_transition_travel("rift-1", "travel-1", "player:7")
    await integration.leave_transition_travel("rift-1", "travel-1", "player:7")
    assert await integration.get_transition_travel_participants("rift-1", "travel-1") == {"player:7"}
    await integration.join_transition_encounter("rift-1", "encounter-1", "player:7")
    await integration.leave_transition_encounter("rift-1", "encounter-1", "player:7")
    assert await integration.get_transition_encounter_participants("rift-1", "encounter-1") == {"player:7"}
    await integration.clear_node_presence("rift-1", "z01:1_2")
    await integration.clear_transition_travel_presence("rift-1", "travel-1")
    await integration.clear_transition_encounter_presence("rift-1", "encounter-1")

    assert [call[0] for call in instance_store.calls] == [
        "save_instance",
        "require_instance",
        "patch_node_event",
        "mark_node_cleared",
        "set_gate_state",
        "set_heart_state",
    ]
    assert [call[0] for call in session_store.calls] == [
        "create_session",
        "save_session",
        "get_session",
        "require_session",
        "set_position",
        "set_visited",
        "set_discovered",
        "start_travel",
        "interrupt_travel",
        "complete_travel",
        "set_active_encounter",
        "clear_active_encounter",
    ]
    assert [call[0] for call in presence_store.calls] == [
        "enter_node",
        "leave_node",
        "move_node",
        "get_node_occupants",
        "join_travel",
        "leave_travel",
        "get_travel_participants",
        "join_encounter",
        "leave_encounter",
        "get_encounter_participants",
        "clear_node_presence",
        "clear_travel_presence",
        "clear_encounter_presence",
    ]


@pytest.mark.unit
async def test_runtime_integration_wraps_storage_not_found_errors() -> None:
    instance_store = FakeInstanceStore()
    session_store = FakeSessionStore()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=FakePresenceStore(),
    )

    instance_store.missing = True
    with pytest.raises(RiftRuntimeNotFoundError, match="Rift instance not found: missing-rift"):
        await integration.require_instance("missing-rift")

    session_store.missing = True
    with pytest.raises(RiftRuntimeNotFoundError, match="Rift run session not found: missing-session"):
        await integration.require_run_session("missing-session")


@pytest.mark.unit
async def test_runtime_integration_flushes_one_mongo_snapshot_and_updates_membership_index() -> None:
    runtime = _runtime_payload("rift-1")
    instance_store = FakeInstanceStore()
    instance_store.runtime = runtime
    session_store = FakeSessionStore()
    session_store.sessions["run-1"] = {
        "rift_session_id": "run-1",
        "rift_instance_id": "rift-1",
        "participant_ref": "char:1",
        "current_node_id": "z01:0_0",
        "active_encounter_id": None,
    }
    presence_store = FakePresenceStore()
    await presence_store.enter_node("rift-1", "z01:0_0", "char:1")
    memberships = FakeMembershipRepository()
    memberships.records["run-1"] = FakeMembership(
        rift_instance_id="rift-1",
        rift_session_id="run-1",
        participant_ref="char:1",
    )
    snapshots = FakeSnapshotRepository()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=presence_store,
        membership_repository=memberships,  # type: ignore[arg-type]
        snapshot_repository=snapshots,  # type: ignore[arg-type]
    )

    result = await integration.flush_runtime_snapshot("rift-1")

    assert result == {
        "status": "ok",
        "rift_instance_id": "rift-1",
        "mongo_snapshot_id": "rift-runtime-snapshot:rift-1",
        "snapshot_version": 1,
    }
    assert snapshots.upserts[0]["instance"]["rift_instance_id"] == "rift-1"
    assert snapshots.upserts[0]["sessions"]["run-1"]["current_node_id"] == "z01:0_0"
    assert snapshots.upserts[0]["presence"]["nodes"]["z01:0_0"] == ["char:1"]
    assert memberships.snapshot_updates == [
        {
            "rift_instance_id": "rift-1",
            "mongo_snapshot_id": "rift-runtime-snapshot:rift-1",
            "snapshot_version": 1,
            "participant_summaries": {
                "run-1": {"current_node_id": "z01:0_0", "active_encounter_id": None},
            },
        }
    ]


@pytest.mark.unit
async def test_runtime_integration_restore_uses_redis_short_path_without_reading_mongo() -> None:
    memberships = FakeMembershipRepository()
    memberships.records["run-1"] = FakeMembership(
        rift_instance_id="rift-1",
        rift_session_id="run-1",
        participant_ref="char:1",
        mongo_snapshot_id="snapshot-1",
    )
    snapshots = FakeSnapshotRepository()
    instance_store = FakeInstanceStore()
    session_store = FakeSessionStore()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=FakePresenceStore(),
        membership_repository=memberships,  # type: ignore[arg-type]
        snapshot_repository=snapshots,  # type: ignore[arg-type]
        restore_lock=FakeRestoreLock(),  # type: ignore[arg-type]
    )

    restored = await integration.restore_participant_rift("char:1")

    assert restored == {"status": "already_live", "rift_instance_id": "rift-1", "rift_session_id": "run-1"}
    assert snapshots.reads == []


@pytest.mark.unit
async def test_runtime_integration_restore_reads_mongo_once_under_lock_and_rebuilds_presence() -> None:
    memberships = FakeMembershipRepository()
    memberships.records["run-1"] = FakeMembership(
        rift_instance_id="rift-1",
        rift_session_id="run-1",
        participant_ref="char:1",
        mongo_snapshot_id="snapshot-1",
    )
    snapshots = FakeSnapshotRepository()
    snapshots.snapshots["rift-1"] = {
        "rift_instance_id": "rift-1",
        "snapshot_version": 7,
        "instance": _runtime_payload("rift-1"),
        "sessions": {
            "run-1": {
                "rift_session_id": "run-1",
                "rift_instance_id": "rift-1",
                "participant_ref": "char:1",
                "current_node_id": "z01:0_0",
            },
            "run-2": {
                "rift_session_id": "run-2",
                "rift_instance_id": "rift-1",
                "participant_ref": "char:2",
                "current_node_id": "z01:0_1",
            },
        },
        "presence": {},
    }
    instance_store = FakeInstanceStore()
    instance_store.missing = True
    session_store = FakeSessionStore()
    presence_store = FakePresenceStore()
    restore_lock = FakeRestoreLock()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=presence_store,
        membership_repository=memberships,  # type: ignore[arg-type]
        snapshot_repository=snapshots,  # type: ignore[arg-type]
        restore_lock=restore_lock,  # type: ignore[arg-type]
    )

    restored = await integration.restore_participant_rift("char:1")

    assert restored == {"status": "restored", "rift_instance_id": "rift-1", "rift_session_id": "run-1"}
    assert snapshots.reads == ["rift-1"]
    assert restore_lock.calls == ["rift-1"]
    assert ("create_session", snapshots.snapshots["rift-1"]["sessions"]["run-1"]) in session_store.calls
    assert ("create_session", snapshots.snapshots["rift-1"]["sessions"]["run-2"]) in session_store.calls
    assert presence_store.nodes[("rift-1", "z01:0_0")] == {"char:1"}
    assert presence_store.nodes[("rift-1", "z01:0_1")] == {"char:2"}


@pytest.mark.unit
async def test_runtime_integration_flushes_dirty_rift_run_to_mongo_snapshot_and_clears_marker() -> None:
    instance_store = FakeInstanceStore()
    instance_store.runtime = _runtime_payload("rift-1")
    session_store = FakeSessionStore()
    session_store.session = {
        "rift_session_id": "run-1",
        "rift_instance_id": "rift-1",
        "participant_ref": "char:1",
        "current_node_id": "z01:0_0",
        "active_encounter_id": None,
        "is_dirty": True,
        "dirty": {"dirty": True, "reason": "travel_completed"},
    }
    memberships = FakeMembershipRepository()
    memberships.records["run-1"] = FakeMembership(
        rift_instance_id="rift-1",
        rift_session_id="run-1",
        participant_ref="char:1",
    )
    snapshots = FakeSnapshotRepository()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=FakePresenceStore(),
        membership_repository=memberships,  # type: ignore[arg-type]
        snapshot_repository=snapshots,  # type: ignore[arg-type]
    )

    result = await integration.flush_dirty_run_session("run-1")

    assert result == {
        "status": "ok",
        "rift_session_id": "run-1",
        "rift_instance_id": "rift-1",
        "mongo_snapshot_id": "rift-runtime-snapshot:rift-1",
        "snapshot_version": 1,
    }
    assert snapshots.upserts
    assert ("clear_dirty", "run-1") in session_store.calls


@pytest.mark.unit
async def test_runtime_integration_snapshot_flush_requires_configured_repositories() -> None:
    integration = RiftRuntimeIntegration(
        instance_store=FakeInstanceStore(),
        session_store=FakeSessionStore(),
        presence_store=FakePresenceStore(),
    )

    with pytest.raises(RuntimeError, match="Rift snapshot repository is not configured"):
        await integration.flush_runtime_snapshot("rift-1")


def _runtime_payload(rift_instance_id: str) -> dict[str, Any]:
    return {
        "rift_instance_id": rift_instance_id,
        "setting": {"setting_key": "starter_rift"},
        "current_node_id": "z01:0_0",
    }
