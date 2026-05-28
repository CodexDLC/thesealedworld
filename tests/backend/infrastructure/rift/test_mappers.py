from __future__ import annotations

import pytest

from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.runtime.generation import build_zone_runtime
from src.backend.infrastructure.rift.mappers import RiftInstanceStateMapper, RiftRunStateMapper


@pytest.mark.unit
def test_instance_state_mapper_splits_runtime_into_restore_blocks() -> None:
    runtime = _runtime()
    mapper = RiftInstanceStateMapper()
    state = mapper.to_model(runtime)
    restored = mapper.to_runtime(state)

    assert state.rift_instance_id == runtime.rift_instance_id
    assert state.setting_key == "starter_rift"
    assert state.zones_json["nodes"]
    assert state.zones_json["placements"]
    assert state.graph_json["passage_edges"]
    assert "void_coords" in state.graph_json
    assert state.nodes_state_json["node_events"] == runtime.node_events
    assert state.runtime_flags_json == {"flags": sorted(runtime.runtime_flags)}
    assert state.state_meta_json["setting_snapshot"]["setting_key"] == "starter_rift"
    assert state.state_meta_json["population_context"]["source"] == "rift_static"
    assert state.state_meta_json["population_context"]["context_hash"]
    assert state.state_meta_json["cold_restore_policy"]["current_position_source"] == "rift_run_state"
    assert restored.rift_instance_id == runtime.rift_instance_id
    assert restored.nodes.keys() == runtime.nodes.keys()
    assert restored.passage_edges.keys() == runtime.passage_edges.keys()
    assert restored.current_node_id == runtime.start_node_id


@pytest.mark.unit
def test_run_state_mapper_keeps_position_and_drops_active_travel_as_restore_source() -> None:
    payload = {
        "rift_session_id": "run-1",
        "owner_type": "party",
        "owner_id": "party:7",
        "rift_instance_id": "rift-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z02",
        "current_node_id": "z02:1_1",
        "previous_node_id": "z02:1_0",
        "heading": "south",
        "visited_node_ids": ["z02:1_0", "z02:1_1"],
        "discovered_node_ids": ["z02:1_0", "z02:1_1", "z02:2_1"],
        "active_travel": {"travel_id": "trv-1", "status": "moving"},
        "active_encounter_id": "enc-1",
        "entry_context": {"entry_world_location_id": "world:1"},
        "last_travel": {"event_type": "none"},
    }

    mapper = RiftRunStateMapper()
    state = mapper.from_session_payload(payload)
    restored = mapper.to_session_payload(state)

    assert state.rift_run_id == "run-1"
    assert state.participant_scope == "party"
    assert state.participant_ref == "party:7"
    assert state.current_zone_key == "z02"
    assert state.current_node_id == "z02:1_1"
    assert state.active_encounter_id == "enc-1"
    assert state.entry_context_json == {"entry_world_location_id": "world:1"}
    assert "active_travel" not in state.run_state_json
    assert state.run_state_json["restore_policy"]["active_travel"] == "drop_to_current_node"
    assert restored["rift_session_id"] == "run-1"
    assert restored["rift_instance_id"] == "rift-1"
    assert restored["current_node_id"] == "z02:1_1"
    assert restored["active_travel"] is None
    assert restored["last_travel"] == {"event_type": "none"}


def _runtime():
    resources = RiftResourceLoader()
    return build_zone_runtime(
        setting=resources.load_setting("starter_rift"),
        pool_nodes=resources.load_node_pool("starter_rift"),
        scale_preset=resources.load_scale_presets()["medium"],
        assembly_preset=resources.load_zone_assembly_presets()["grid_5x5_active_15"],
        seed="rift-mapper-check",
        debug=True,
    )
