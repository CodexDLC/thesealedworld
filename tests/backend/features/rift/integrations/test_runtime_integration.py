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

    async def save_instance(self, runtime: Any) -> None:
        self.calls.append(("save_instance", runtime))

    async def require_instance(self, rift_instance_id: str) -> Any:
        self.calls.append(("require_instance", rift_instance_id))
        if self.missing:
            raise RiftInstanceNotFoundError(f"Rift instance not found: {rift_instance_id}")
        return self.runtime

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

    async def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_session", payload))
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
        return self.session or {"rift_session_id": rift_session_id}

    async def require_session(self, rift_session_id: str) -> dict[str, Any]:
        self.calls.append(("require_session", rift_session_id))
        if self.missing:
            raise RiftRunSessionNotFoundError(f"Rift run session not found: {rift_session_id}")
        return self.session or {"rift_session_id": rift_session_id}

    async def mark_dirty(self, rift_session_id: str, *, reason: str, paths: list[str]) -> None:
        self.calls.append(("mark_dirty", rift_session_id, reason, paths))

    async def clear_dirty(self, rift_session_id: str) -> None:
        self.calls.append(("clear_dirty", rift_session_id))

    async def scan_dirty(self, *, limit: int = 100) -> list[str]:
        self.calls.append(("scan_dirty", limit))
        return ["run-1"]

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

    async def enter_node(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.calls.append(("enter_node", rift_instance_id, node_id, participant_ref))

    async def leave_node(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.calls.append(("leave_node", rift_instance_id, node_id, participant_ref))

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
        return {"player:7"}

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

    async def clear_travel_presence(self, rift_instance_id: str, travel_id: str) -> None:
        self.calls.append(("clear_travel_presence", rift_instance_id, travel_id))

    async def clear_encounter_presence(self, rift_instance_id: str, encounter_id: str) -> None:
        self.calls.append(("clear_encounter_presence", rift_instance_id, encounter_id))


class FakeStateRepository:
    def __init__(self) -> None:
        self.upserts: list[Any] = []
        self.records: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self.records.get(key)

    async def upsert(self, state: Any) -> Any:
        self.upserts.append(state)
        return state


class FakeInstanceStateMapper:
    def to_model(self, runtime: Any, *, status: str = "active") -> dict[str, Any]:
        return {"kind": "instance_state", "runtime": runtime, "status": status}

    def to_runtime(self, state: dict[str, Any]) -> Any:
        return state["runtime"]


class FakeRunStateMapper:
    def from_session_payload(self, payload: dict[str, Any], *, status: str | None = None) -> dict[str, Any]:
        return {"kind": "run_state", "payload": payload, "status": status}

    def to_session_payload(self, state: dict[str, Any]) -> dict[str, Any]:
        return dict(state["payload"])


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
async def test_runtime_integration_restores_missing_redis_state_from_db_backup() -> None:
    instance_store = FakeInstanceStore()
    instance_store.missing = True
    session_store = FakeSessionStore()
    session_store.missing = True
    instance_repository = FakeStateRepository()
    instance_repository.records["rift-1"] = {"runtime": instance_store.runtime}
    run_repository = FakeStateRepository()
    run_repository.records["run-1"] = {"payload": {"rift_session_id": "run-1", "rift_instance_id": "rift-1"}}
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=FakePresenceStore(),
        instance_state_repository=instance_repository,  # type: ignore[arg-type]
        run_state_repository=run_repository,  # type: ignore[arg-type]
        instance_state_mapper=FakeInstanceStateMapper(),  # type: ignore[arg-type]
        run_state_mapper=FakeRunStateMapper(),  # type: ignore[arg-type]
    )

    assert await integration.require_instance("rift-1") is instance_store.runtime
    assert await integration.require_run_session("run-1") == {"rift_session_id": "run-1", "rift_instance_id": "rift-1"}
    assert ("save_instance", instance_store.runtime) in instance_store.calls
    assert any(call[0] == "create_session" for call in session_store.calls)


@pytest.mark.unit
async def test_runtime_integration_internal_mode_can_save_instance_to_redis_and_db() -> None:
    instance_store = FakeInstanceStore()
    instance_repository = FakeStateRepository()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=FakeSessionStore(),
        presence_store=FakePresenceStore(),
        instance_state_repository=instance_repository,  # type: ignore[arg-type]
        instance_state_mapper=FakeInstanceStateMapper(),  # type: ignore[arg-type]
    )

    result = await integration.save_instance_runtime(instance_store.runtime, mode="redis_and_db", status="paused")

    assert [call[0] for call in instance_store.calls] == ["save_instance"]
    assert result == {"kind": "instance_state", "runtime": instance_store.runtime, "status": "paused"}
    assert instance_repository.upserts == [result]


@pytest.mark.unit
async def test_runtime_integration_internal_mode_can_save_run_state_to_db_only() -> None:
    session_store = FakeSessionStore()
    run_repository = FakeStateRepository()
    integration = RiftRuntimeIntegration(
        instance_store=FakeInstanceStore(),
        session_store=session_store,
        presence_store=FakePresenceStore(),
        run_state_repository=run_repository,  # type: ignore[arg-type]
        run_state_mapper=FakeRunStateMapper(),  # type: ignore[arg-type]
    )
    payload = {"rift_session_id": "run-1"}

    result = await integration.save_run_session_runtime(payload, mode="db_only", status="active")

    assert session_store.calls == []
    assert result == {"kind": "run_state", "payload": payload, "status": "active"}
    assert run_repository.upserts == [result]


@pytest.mark.unit
async def test_runtime_integration_flushes_dirty_rift_run_to_db_and_clears_marker() -> None:
    instance_store = FakeInstanceStore()
    session_store = FakeSessionStore()
    session_store.session = {
        "rift_session_id": "run-1",
        "rift_instance_id": "rift-1",
        "is_dirty": True,
        "dirty": {"dirty": True, "reason": "travel_completed"},
    }
    instance_repository = FakeStateRepository()
    run_repository = FakeStateRepository()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=FakePresenceStore(),
        instance_state_repository=instance_repository,  # type: ignore[arg-type]
        run_state_repository=run_repository,  # type: ignore[arg-type]
        instance_state_mapper=FakeInstanceStateMapper(),  # type: ignore[arg-type]
        run_state_mapper=FakeRunStateMapper(),  # type: ignore[arg-type]
    )

    result = await integration.flush_dirty_run_session("run-1")

    assert result == {"status": "ok", "rift_session_id": "run-1", "rift_instance_id": "rift-1"}
    assert instance_repository.upserts == [
        {"kind": "instance_state", "runtime": instance_store.runtime, "status": "active"}
    ]
    assert run_repository.upserts == [
        {"kind": "run_state", "payload": session_store.session, "status": "active"}
    ]
    assert ("clear_dirty", "run-1") in session_store.calls


@pytest.mark.unit
async def test_runtime_integration_db_modes_require_configured_repositories() -> None:
    integration = RiftRuntimeIntegration(
        instance_store=FakeInstanceStore(),
        session_store=FakeSessionStore(),
        presence_store=FakePresenceStore(),
    )

    with pytest.raises(RuntimeError, match="Rift instance state repository is not configured"):
        await integration.save_instance_runtime(object(), mode="db_only")

    with pytest.raises(RuntimeError, match="Rift run state repository is not configured"):
        await integration.save_run_session_runtime({"rift_session_id": "run-1"}, mode="db_only")
