from __future__ import annotations

from copy import deepcopy
from typing import Any

RIFT_COMPOSITION_POLICY_PRESETS: dict[str, dict[str, Any]] = {
    "ordinary": {
        "allowed_roles": ["minion"],
        "required_roles": [],
        "min_units": 1,
        "max_units": 3,
        "allow_repeated_members": True,
        "prefer_distinct_members": True,
    },
    "ordinary_node": {
        "allowed_roles": ["minion"],
        "required_roles": [],
        "min_units": 1,
        "max_units": 3,
        "allow_repeated_members": True,
        "prefer_distinct_members": True,
    },
    "transition": {
        "allowed_roles": ["minion"],
        "required_roles": [],
        "min_units": 1,
        "max_units": 3,
        "allow_repeated_members": True,
        "prefer_distinct_members": True,
    },
    "key_guard": {
        "allowed_roles": ["veteran", "elite"],
        "required_roles": ["elite"],
        "min_units": 1,
        "max_units": 2,
        "allow_repeated_members": False,
    },
    "heart_guard": {
        "allowed_roles": ["boss", "elite", "veteran", "minion"],
        "required_roles": ["boss"],
        "min_units": 1,
        "max_units": 4,
        "allow_repeated_members": True,
        "prefer_distinct_members": True,
    },
    "boss_solo": {
        "allowed_roles": ["boss"],
        "required_roles": ["boss"],
        "min_units": 1,
        "max_units": 1,
        "allow_repeated_members": False,
    },
    "boss_with_minions": {
        "allowed_roles": ["boss", "minion", "veteran"],
        "required_roles": ["boss"],
        "min_units": 1,
        "max_units": 4,
        "allow_repeated_members": True,
        "prefer_distinct_members": True,
    },
}

_FAMILY_RULE_KINDS = {"", "node_event"}


def composition_policy_for_encounter_kind(kind: str | None) -> dict[str, Any] | None:
    normalized = str(kind or "").strip()
    if normalized in _FAMILY_RULE_KINDS:
        return None
    preset = RIFT_COMPOSITION_POLICY_PRESETS.get(normalized)
    return deepcopy(preset) if preset is not None else None
