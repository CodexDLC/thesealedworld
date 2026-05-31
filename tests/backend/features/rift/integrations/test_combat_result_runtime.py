from __future__ import annotations

from typing import Any

import pytest

from src.backend.features.rift.dto import RiftPassageEdgeDTO, RiftZoneCellDTO, RiftZoneRuntimeDTO
from src.backend.features.rift.integrations import RiftRuntimeIntegration


class FakeInstanceStore:
    def __init__(self, runtime: RiftZoneRuntimeDTO) -> None:
        self.runtime = runtime
        self.saved: list[RiftZoneRuntimeDTO] = []

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        self.runtime = runtime
        self.saved.append(runtime)

    async def require_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO:
        assert rift_instance_id == self.runtime.rift_instance_id
        return self.runtime


class FakeSessionStore:
    def __init__(self, session: dict[str, Any]) -> None:
        self.session = dict(session)
        self.saved: list[dict[str, Any]] = []

    async def require_session(self, rift_session_id: str) -> dict[str, Any]:
        assert rift_session_id == self.session["rift_session_id"]
        return dict(self.session)

    async def save_session(
        self,
        payload: dict[str, Any],
        *,
        dirty_reason: str | None = None,
        dirty_paths: list[str] | None = None,
    ) -> None:
        self.session = dict(payload)
        self.saved.append(dict(payload))

    async def clear_active_encounter(self, rift_session_id: str) -> None:
        assert rift_session_id == self.session["rift_session_id"]
        self.session["active_encounter_id"] = None


class FakePresenceStore:
    def __init__(self) -> None:
        self.moved: list[tuple[str, str | None, str, str]] = []
        self.cleared_encounters: list[tuple[str, str]] = []
        self.cleared_travels: list[tuple[str, str]] = []

    async def move_node(
        self,
        rift_instance_id: str,
        *,
        from_node_id: str | None,
        to_node_id: str,
        participant_ref: str,
    ) -> None:
        self.moved.append((rift_instance_id, from_node_id, to_node_id, participant_ref))

    async def clear_encounter_presence(self, rift_instance_id: str, encounter_id: str) -> None:
        self.cleared_encounters.append((rift_instance_id, encounter_id))

    async def clear_travel_presence(self, rift_instance_id: str, travel_id: str) -> None:
        self.cleared_travels.append((rift_instance_id, travel_id))


@pytest.mark.asyncio
async def test_apply_transition_combat_result_completes_interrupted_travel() -> None:
    runtime = _two_node_runtime().model_copy(
        update={
            "active_travel": {
                "travel_id": "trv-1",
                "status": "interrupted",
                "tick_result": "combat",
                "from_node_id": "node-start",
                "to_node_id": "node-next",
                "kind": "exploration",
                "duration_ms": 2000,
                "tick_interval_ms": 2000,
                "checks_done": 1,
                "checks_total": 1,
                "remaining_ms": 0,
                "direction": "north",
            }
        }
    )
    session_store = FakeSessionStore(
        {
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "current_node_id": "node-start",
            "visited_node_ids": ["node-start"],
            "active_travel": runtime.active_travel,
            "participant_ref": "char:7",
            "active_encounter_id": "combat-1",
        }
    )
    presence = FakePresenceStore()
    integration = RiftRuntimeIntegration(
        instance_store=FakeInstanceStore(runtime),
        session_store=session_store,
        presence_store=presence,
    )

    result = await integration.apply_combat_result(
        combat_id="",
        result="victory",
        rift_session_id="rift-run-1",
        rift_instance_id="rift-instance-1",
        event_scope="transition",
        travel_id="trv-1",
    )

    assert result["applied"] is True
    assert session_store.saved[-1]["current_node_id"] == "node-next"
    assert session_store.saved[-1]["previous_node_id"] == "node-start"
    assert session_store.saved[-1]["active_travel"] is None
    assert session_store.saved[-1]["active_encounter_id"] is None
    assert presence.moved == [("rift-instance-1", "node-start", "node-next", "char:7")]
    assert presence.cleared_encounters == [("rift-instance-1", "combat-1")]
    assert presence.cleared_travels == [("rift-instance-1", "trv-1")]


@pytest.mark.asyncio
async def test_apply_node_entry_combat_result_clears_event_and_grants_flags() -> None:
    runtime = _two_node_runtime().model_copy(
        update={
            "current_node_id": "node-next",
            "visited_node_ids": {"node-start", "node-next"},
            "node_events": {
                "node-next": {
                    "event_key": "guard-1",
                    "event_type": "combat",
                    "state": "ready",
                    "grants_flags": ["heart_guard_cleared"],
                }
            },
            "gate_states": {
                "heart_gate": {
                    "state": "locked",
                    "requirement": {"type": "rift_flag", "flag": "heart_guard_cleared"},
                }
            },
        }
    )
    session_store = FakeSessionStore(
        {
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "current_node_id": "node-next",
            "visited_node_ids": ["node-start", "node-next"],
            "participant_ref": "char:7",
            "active_encounter_id": "combat-guard",
        }
    )
    integration = RiftRuntimeIntegration(
        instance_store=FakeInstanceStore(runtime),
        session_store=session_store,
        presence_store=FakePresenceStore(),
    )

    result = await integration.apply_combat_result(
        combat_id="combat-guard",
        result="victory",
        rift_session_id="rift-run-1",
        rift_instance_id="rift-instance-1",
        event_scope="node_entry",
        event_key="guard-1",
    )

    saved_runtime = integration.instance_store.saved[-1]
    assert result["applied"] is True
    assert saved_runtime.node_events["node-next"]["state"] == "cleared"
    assert "heart_guard_cleared" in saved_runtime.runtime_flags
    assert saved_runtime.gate_states["heart_gate"]["state"] == "open"
    assert session_store.saved[-1]["active_encounter_id"] is None


@pytest.mark.asyncio
async def test_apply_combat_result_defeat_clears_encounter_without_resolving_event() -> None:
    """Regression: defeat must NOT cleared events or open gates — only release the encounter."""
    runtime = _two_node_runtime().model_copy(
        update={
            "current_node_id": "node-next",
            "visited_node_ids": {"node-start", "node-next"},
            "node_events": {
                "node-next": {
                    "event_key": "guard-1",
                    "event_type": "combat",
                    "state": "ready",
                    "grants_flags": ["heart_guard_cleared"],
                }
            },
            "gate_states": {
                "heart_gate": {
                    "state": "locked",
                    "requirement": {"type": "rift_flag", "flag": "heart_guard_cleared"},
                }
            },
            "active_travel": {
                "travel_id": "trv-1",
                "status": "interrupted",
                "tick_result": "combat",
                "from_node_id": "node-start",
                "to_node_id": "node-next",
                "kind": "exploration",
                "duration_ms": 2000,
                "tick_interval_ms": 2000,
                "checks_done": 1,
                "checks_total": 1,
                "remaining_ms": 0,
                "direction": "north",
            },
        }
    )
    session_store = FakeSessionStore(
        {
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "current_node_id": "node-next",
            "visited_node_ids": ["node-start", "node-next"],
            "participant_ref": "char:7",
            "active_encounter_id": "combat-guard",
            "active_travel": runtime.active_travel,
        }
    )
    instance_store = FakeInstanceStore(runtime)
    presence = FakePresenceStore()
    integration = RiftRuntimeIntegration(
        instance_store=instance_store,
        session_store=session_store,
        presence_store=presence,
    )

    result = await integration.apply_combat_result(
        combat_id="combat-guard",
        result="defeat",
        rift_session_id="rift-run-1",
        rift_instance_id="rift-instance-1",
        event_scope="node_entry",
        event_key="guard-1",
    )

    assert result["applied"] is True
    assert result["result"] == "defeat"
    # Encounter binding released, but no instance save occurred (no progression).
    assert instance_store.saved == []
    # Session was saved with cleared encounter + travel, current node unchanged.
    saved_session = session_store.saved[-1]
    assert saved_session["active_encounter_id"] is None
    assert saved_session["active_travel"] is None
    assert saved_session["current_node_id"] == "node-next"
    assert presence.cleared_encounters == [("rift-instance-1", "combat-guard")]


@pytest.mark.asyncio
async def test_apply_combat_result_is_idempotent_when_rift_session_is_already_unlocked() -> None:
    runtime = _two_node_runtime()
    session_store = FakeSessionStore(
        {
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "current_node_id": "node-start",
            "visited_node_ids": ["node-start"],
            "active_encounter_id": None,
        }
    )
    integration = RiftRuntimeIntegration(
        instance_store=FakeInstanceStore(runtime),
        session_store=session_store,
        presence_store=FakePresenceStore(),
    )

    result = await integration.apply_combat_result(
        combat_id="combat-1",
        result="victory",
        rift_session_id="rift-run-1",
        rift_instance_id="rift-instance-1",
        event_scope="transition",
        travel_id="trv-1",
    )

    assert result == {"applied": False, "reason": "rift_encounter_already_resolved"}
    assert session_store.saved == []


def _two_node_runtime() -> RiftZoneRuntimeDTO:
    return RiftZoneRuntimeDTO(
        rift_instance_id="rift-instance-1",
        zone_instance_id="zone-1",
        zone_canvas_key="starter",
        scale_preset_key="starter_5x5",
        assembly_preset_key="starter",
        setting={"title": "Рваный тракт", "tier": 1},
        nodes={
            "node-start": RiftZoneCellDTO(
                node_id="node-start",
                x=2,
                y=2,
                pool_node_id="pool-start",
                node_hex="A",
                title="Сухая дорога",
                description="Стартовая точка.",
            ),
            "node-next": RiftZoneCellDTO(
                node_id="node-next",
                x=2,
                y=1,
                pool_node_id="pool-next",
                node_hex="B",
                title="Разбитая повозка",
                description="Пыль и щепки.",
            ),
        },
        cells_by_coord={"2:2": "node-start", "2:1": "node-next"},
        passage_edges={
            "node-start:north": RiftPassageEdgeDTO(
                from_node_id="node-start",
                to_node_id="node-next",
                absolute_direction="north",
                state="open",
            )
        },
        start_node_id="node-start",
        finish_node_id="node-next",
        current_node_id="node-start",
        visited_node_ids={"node-start"},
    )
