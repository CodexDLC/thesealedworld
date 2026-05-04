from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.backend.features.scenario.dto.master import QuestMasterSchema, QuestNodeSchema, ScenarioNodeType


def validate_scenario_fixtures(root: Path) -> list[str]:
    base_dir = root / "src" / "backend" / "features" / "scenario" / "resources" / "json"
    errors: list[str] = []
    if not base_dir.exists():
        return errors

    for fixture_dir in sorted(path for path in base_dir.iterdir() if path.is_dir()):
        errors.extend(_validate_fixture_dir(fixture_dir))

    return errors


def _validate_fixture_dir(fixture_dir: Path) -> list[str]:
    errors: list[str] = []
    master_file = fixture_dir / "master.json"
    if not master_file.exists():
        return [f"{fixture_dir}: missing master.json"]

    try:
        master = QuestMasterSchema.model_validate(_read_json(master_file))
    except (ValidationError, ValueError) as exc:
        return [f"{master_file}: invalid master: {exc}"]

    node_files = _discover_node_files(fixture_dir)
    if not node_files:
        errors.append(f"{fixture_dir}: no node json files found")
        return errors

    nodes: list[dict[str, Any]] = []
    for node_file in node_files:
        try:
            raw_nodes = _read_json(node_file)
            if not isinstance(raw_nodes, list):
                errors.append(f"{node_file}: expected a list of nodes")
                continue
            for raw_node in raw_nodes:
                raw_node = {**raw_node, "quest_key": master.quest_key}
                node = QuestNodeSchema.model_validate(raw_node).model_dump(mode="json")
                nodes.append(node)
                if "node_type" not in raw_node:
                    errors.append(f"{node_file}:{raw_node.get('node_key', '<unknown>')}: missing explicit node_type")
        except (ValidationError, ValueError) as exc:
            errors.append(f"{node_file}: invalid nodes: {exc}")

    errors.extend(_validate_graph(fixture_dir, master.start_node_id, nodes))
    return errors


def _validate_graph(fixture_dir: Path, start_node_id: str, nodes: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    by_key: dict[str, dict[str, Any]] = {}
    tags: dict[str, list[str]] = {}

    for node in nodes:
        node_key = node["node_key"]
        if node_key in by_key:
            errors.append(f"{fixture_dir}: duplicate node_key={node_key}")
        by_key[node_key] = node
        for tag in node.get("tags", []):
            tags.setdefault(tag, []).append(node_key)

    if start_node_id not in by_key:
        errors.append(f"{fixture_dir}: start_node_id not found: {start_node_id}")

    for node in nodes:
        node_key = node["node_key"]
        node_type = node.get("node_type")
        actions = _actions(node)

        if node_type == ScenarioNodeType.ROUTER.value:
            if "auto" not in actions:
                errors.append(f"{fixture_dir}:{node_key}: router node must define auto action")
            visible = [action_id for action_id in actions if action_id != "auto"]
            if visible:
                errors.append(f"{fixture_dir}:{node_key}: router node has visible actions: {visible}")

        if node_type == ScenarioNodeType.EXIT.value:
            if not any(action.get("type") == "finish_quest" for action in actions.values()):
                errors.append(f"{fixture_dir}:{node_key}: exit node must contain finish_quest action")

        for action_id, action in actions.items():
            for target in _action_targets(action):
                if target.startswith("pool:"):
                    pool_tag = target.split(":", 1)[1]
                    if pool_tag not in tags:
                        errors.append(f"{fixture_dir}:{node_key}:{action_id}: missing pool tag: {pool_tag}")
                elif target not in by_key:
                    errors.append(f"{fixture_dir}:{node_key}:{action_id}: missing target node: {target}")

    return errors


def _actions(node: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actions: dict[str, dict[str, Any]] = {}
    for action in node.get("actions", []):
        action_id = action.get("action_id")
        if action_id:
            actions[action_id] = action
    actions.update(node.get("actions_logic", {}))
    return actions


def _action_targets(action: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    if action.get("to_node"):
        targets.append(action["to_node"])
    for branch in action.get("branching", []):
        if branch.get("to_node"):
            targets.append(branch["to_node"])
    return targets


def _discover_node_files(fixture_dir: Path) -> list[Path]:
    nodes_dir = fixture_dir / "nodes"
    if nodes_dir.exists():
        return sorted(nodes_dir.glob("*.json"))
    return sorted(fixture_dir.glob("nodes_*.json"))


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
