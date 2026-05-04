"""One-shot fixer: restore lost fields in awakening_rift node parts from the legacy single-file source.

Reads the legacy single-file scenario at temp/.../tutorial_arrival.json and merges the missing
fields (tags, selection_requirements, per-action math/branching) into the split part files at
src/backend/features/scenario/resources/json/awakening_rift/nodes_part_*.json.

Preserves user-expanded fields in the part files (text, system_messages, avatar, icon, action labels).

Run from repo root:
    python tools/fix_awakening_rift_from_legacy.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY = REPO_ROOT / "temp/backend/domains/user_features/scenario/resources/json/tutorial_arrival.json"
PARTS_DIR = REPO_ROOT / "src/backend/features/scenario/resources/json/awakening_rift"
PART_FILES = sorted(PARTS_DIR.glob("nodes_part_*.json"))

CYCLE_TAGS = {"cycle_1", "cycle_2", "cycle_3"}


def load_legacy() -> dict[str, dict]:
    data = json.loads(LEGACY.read_text(encoding="utf-8"))
    return {n["node_key"]: n for n in data["nodes"]}


def merge_action(current: dict, legacy: dict) -> dict:
    out = dict(current)
    if "math" in legacy and legacy["math"]:
        out["math"] = legacy["math"]
    if "branching" in legacy and legacy["branching"]:
        out["branching"] = legacy["branching"]
    if "type" in legacy:
        out["type"] = legacy["type"]
    if current.get("action_id") == "auto" and legacy.get("to_node") is not None:
        out["to_node"] = legacy["to_node"]
    return out


def merge_node(current: dict, legacy: dict) -> dict:
    out = dict(current)

    legacy_tags = legacy.get("tags")
    if legacy_tags:
        out["tags"] = list(legacy_tags)
    elif current.get("tags") and any(t in CYCLE_TAGS for t in current["tags"]):
        # legacy router has no tags; strip any cycle_* tag accidentally added
        out["tags"] = [t for t in current["tags"] if t not in CYCLE_TAGS]
        if not out["tags"]:
            out.pop("tags", None)

    if legacy.get("selection_requirements"):
        out["selection_requirements"] = legacy["selection_requirements"]

    legacy_logic = legacy.get("actions_logic") or {}
    actions = current.get("actions") or []
    new_actions = []
    seen_ids: set[str] = set()
    for action in actions:
        aid = action.get("action_id")
        seen_ids.add(aid)
        legacy_action = legacy_logic.get(aid)
        if legacy_action:
            new_actions.append(merge_action(action, legacy_action))
        else:
            new_actions.append(action)
    # Add any legacy-only actions (e.g. "auto" missing in current node) at the front
    extra = []
    for aid, legacy_action in legacy_logic.items():
        if aid in seen_ids:
            continue
        # Build a current-style action dict from legacy
        built = {
            "action_id": aid,
            "label": legacy_action.get("label", ""),
            "icon": "default",
            "to_node": legacy_action.get("to_node"),
        }
        if legacy_action.get("math"):
            built["math"] = legacy_action["math"]
        if legacy_action.get("branching"):
            built["branching"] = legacy_action["branching"]
        if legacy_action.get("type"):
            built["type"] = legacy_action["type"]
        extra.append(built)
    if extra:
        new_actions = extra + new_actions
    out["actions"] = new_actions
    return out


def main() -> None:
    legacy = load_legacy()
    summary: list[str] = []
    for part_path in PART_FILES:
        nodes = json.loads(part_path.read_text(encoding="utf-8"))
        changed = 0
        for i, node in enumerate(nodes):
            key = node["node_key"]
            if key in legacy:
                merged = merge_node(node, legacy[key])
                if merged != node:
                    nodes[i] = merged
                    changed += 1
        part_path.write_text(
            json.dumps(nodes, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary.append(f"{part_path.name}: {changed}/{len(nodes)} nodes updated")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()
