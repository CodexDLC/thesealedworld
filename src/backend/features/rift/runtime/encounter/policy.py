from __future__ import annotations

from copy import deepcopy
from typing import Any

RIFT_COMPOSITION_POLICY_PRESETS: dict[str, dict[str, Any]] = {
    "ordinary": {
        "encounter_kind": "ordinary",
    },
    "ordinary_node": {
        "encounter_kind": "ordinary",
    },
    "transition": {
        "encounter_kind": "ordinary",
    },
    "key_guard": {
        "encounter_kind": "guard",
    },
    "heart_guard": {
        "encounter_kind": "boss",
    },
    "boss_solo": {
        "encounter_kind": "boss",
        "allowed_roles": ["boss"],
        "required_roles": ["boss"],
        "min_units": 1,
        "max_units": 1,
        "allow_repeated_members": False,
    },
    "boss_with_minions": {
        "encounter_kind": "boss",
    },
}

_FAMILY_RULE_KINDS = {"", "node_event"}


def composition_policy_for_encounter_kind(kind: str | None) -> dict[str, Any] | None:
    normalized = str(kind or "").strip()
    if normalized in _FAMILY_RULE_KINDS:
        return None
    preset = RIFT_COMPOSITION_POLICY_PRESETS.get(normalized)
    return deepcopy(preset) if preset is not None else None
