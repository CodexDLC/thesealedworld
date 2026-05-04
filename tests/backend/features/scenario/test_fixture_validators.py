import json
from pathlib import Path
from typing import Any

import pytest

from tools.validators.scenario_fixtures import validate_scenario_fixtures


@pytest.mark.unit
def test_validate_scenario_fixtures_accepts_split_nodes(tmp_path):
    fixture_dir = _fixture_dir(tmp_path, "valid_quest")
    _write_master(fixture_dir, quest_key="valid_quest", start_node_id="start")
    _write_nodes(
        fixture_dir / "nodes" / "00_start.json",
        [
            {
                "node_key": "start",
                "node_type": "exit",
                "text": "Done.",
                "actions": [
                    {
                        "action_id": "finish",
                        "label": "Finish",
                        "type": "finish_quest",
                    },
                ],
            },
        ],
    )

    assert validate_scenario_fixtures(tmp_path) == []


@pytest.mark.unit
def test_validate_scenario_fixtures_reports_missing_type_and_target(tmp_path):
    fixture_dir = _fixture_dir(tmp_path, "broken_quest")
    _write_master(fixture_dir, quest_key="broken_quest", start_node_id="start")
    _write_nodes(
        fixture_dir / "nodes" / "00_start.json",
        [
            {
                "node_key": "start",
                "text": "Broken.",
                "actions": [
                    {
                        "action_id": "next",
                        "label": "Next",
                        "to_node": "missing_node",
                    },
                ],
            },
        ],
    )

    errors = validate_scenario_fixtures(tmp_path)

    assert any("missing explicit node_type" in error for error in errors)
    assert any("missing target node: missing_node" in error for error in errors)


@pytest.mark.unit
def test_validate_scenario_fixtures_requires_router_auto_only(tmp_path):
    fixture_dir = _fixture_dir(tmp_path, "router_quest")
    _write_master(fixture_dir, quest_key="router_quest", start_node_id="router")
    _write_nodes(
        fixture_dir / "nodes" / "00_router.json",
        [
            {
                "node_key": "router",
                "node_type": "router",
                "text": "Choose invisibly.",
                "actions": [
                    {
                        "action_id": "visible",
                        "label": "Visible",
                        "to_node": "done",
                    },
                ],
            },
            {
                "node_key": "done",
                "node_type": "exit",
                "text": "Done.",
                "actions": [
                    {
                        "action_id": "finish",
                        "label": "Finish",
                        "type": "finish_quest",
                    },
                ],
            },
        ],
    )

    errors = validate_scenario_fixtures(tmp_path)

    assert any("router node must define auto action" in error for error in errors)
    assert any("router node has visible actions" in error for error in errors)


def _fixture_dir(root: Path, quest_key: str) -> Path:
    fixture_dir = (
        root
        / "src"
        / "backend"
        / "features"
        / "scenario"
        / "resources"
        / "json"
        / quest_key
    )
    (fixture_dir / "nodes").mkdir(parents=True)
    return fixture_dir


def _write_master(fixture_dir: Path, *, quest_key: str, start_node_id: str) -> None:
    (fixture_dir / "master.json").write_text(
        json.dumps(
            {
                "quest_key": quest_key,
                "display_name": quest_key,
                "start_node_id": start_node_id,
                "status_bar_fields": [],
            },
        ),
        encoding="utf-8",
    )


def _write_nodes(path: Path, nodes: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(nodes), encoding="utf-8")
