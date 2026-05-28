from __future__ import annotations

import pytest

from src.backend.core.database import Base
from src.backend.infrastructure.rift import (
    RiftInstanceState,
    RiftNodePoolRecord,
    RiftPortalKey,
    RiftRunState,
    RiftSetting,
)


@pytest.mark.unit
def test_rift_persistence_models_register_expected_tables() -> None:
    assert RiftSetting.__tablename__ == "rift_settings"
    assert RiftNodePoolRecord.__tablename__ == "rift_node_pool_records"
    assert RiftInstanceState.__tablename__ == "rift_instance_states"
    assert RiftRunState.__tablename__ == "rift_run_states"
    assert RiftPortalKey.__tablename__ == "rift_portal_keys"
    assert {
        "rift_settings",
        "rift_node_pool_records",
        "rift_instance_states",
        "rift_run_states",
        "rift_portal_keys",
    } <= set(Base.metadata.tables)


@pytest.mark.unit
def test_rift_instance_state_splits_runtime_into_top_level_json_blocks() -> None:
    table = RiftInstanceState.__table__

    assert table.primary_key.columns.keys() == ["rift_instance_id"]
    assert "state_json" not in table.c
    assert {
        "zones_json",
        "graph_json",
        "nodes_state_json",
        "objectives_json",
        "runtime_flags_json",
        "state_meta_json",
    } <= set(table.c.keys())
    assert "setting_key" in table.c
    assert "status" in table.c
    assert "scale_preset_key" in table.c
    assert "assembly_preset_key" in table.c


@pytest.mark.unit
def test_rift_portal_key_persists_portal_lifecycle_and_runtime_refs() -> None:
    table = RiftPortalKey.__table__

    assert table.primary_key.columns.keys() == ["portal_id"]
    assert {
        "portal_key",
        "status",
        "source",
        "source_ref",
        "rift_key",
        "entry_mode",
        "owner_id",
        "participant_scope",
        "rift_session_id",
        "rift_instance_id",
        "service_id",
        "source_location_id",
        "exit_target_state",
        "exit_location_id",
        "expires_at",
        "closed_at",
        "archived_at",
        "entry_context_json",
        "exit_policy_json",
        "runtime_refs_json",
        "state_json",
    } <= set(table.c.keys())
    assert "status" in table.c


@pytest.mark.unit
def test_rift_run_state_keeps_position_and_critical_restore_refs() -> None:
    table = RiftRunState.__table__

    assert table.primary_key.columns.keys() == ["rift_run_id"]
    assert "active_travel" not in table.c
    assert {
        "rift_instance_id",
        "participant_scope",
        "participant_ref",
        "status",
        "current_zone_key",
        "current_node_id",
        "previous_node_id",
        "heading",
        "visited_node_ids",
        "discovered_node_ids",
        "active_encounter_id",
        "entry_context_json",
        "run_state_json",
    } <= set(table.c.keys())
