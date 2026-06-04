from __future__ import annotations

import pytest

from src.backend.core.database import Base
from src.backend.infrastructure.rift import (
    RiftMembership,
    RiftNodePoolRecord,
    RiftSetting,
)


@pytest.mark.unit
def test_rift_persistence_models_register_expected_tables() -> None:
    assert RiftSetting.__tablename__ == "rift_settings"
    assert RiftNodePoolRecord.__tablename__ == "rift_node_pool_records"
    assert RiftMembership.__tablename__ == "rift_memberships"
    assert {
        "rift_settings",
        "rift_node_pool_records",
        "rift_memberships",
    } <= set(Base.metadata.tables)


@pytest.mark.unit
def test_rift_static_tables_keep_mongo_document_refs_not_heavy_json_payloads() -> None:
    setting_table = RiftSetting.__table__
    node_table = RiftNodePoolRecord.__table__

    assert "mongo_setting_doc_id" in setting_table.c
    assert "mongo_status" in setting_table.c
    assert "profile_json" not in setting_table.c
    assert "generation_rules_json" not in setting_table.c
    assert "text_vocabulary_json" not in setting_table.c

    assert "mongo_node_doc_id" in node_table.c
    assert "mongo_status" in node_table.c
    assert "approach_view_json" not in node_table.c
    assert "transition_text_json" not in node_table.c
    assert "generation_json" not in node_table.c


@pytest.mark.unit
def test_rift_membership_is_index_and_mongo_snapshot_pointer_not_runtime_backup() -> None:
    table = RiftMembership.__table__

    assert table.primary_key.columns.keys() == ["id"]
    assert {
        "rift_instance_id",
        "rift_session_id",
        "participant_ref",
        "setting_key",
        "status",
        "mongo_snapshot_id",
        "snapshot_version",
        "source",
        "source_ref",
        "current_node_id",
        "active_encounter_id",
        "completed_at",
    } <= set(table.c.keys())
    assert "zones_json" not in table.c
    assert "graph_json" not in table.c
    assert "nodes_state_json" not in table.c
    assert "run_state_json" not in table.c
    assert "entry_context_json" not in table.c
