from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, NotRequired, TypedDict, cast

EncounterDifficulty = Literal["easy", "normal", "hard"]
EncounterKind = Literal["ordinary", "guard", "boss"]
MonsterRole = Literal["minion", "veteran", "elite", "boss"]


class MonsterEncounterProfile(TypedDict):
    budget_multiplier: float
    min_units: int
    max_units: int
    start_role: MonsterRole
    allowed_roles: list[MonsterRole]
    required_roles: list[MonsterRole]
    role_caps: dict[MonsterRole, int]
    upgrade_order: list[MonsterRole]
    allow_repeated_members: bool
    prefer_distinct_members: bool
    build_mode: NotRequired[str]
    upgrade_stages: NotRequired[list[dict[str, Any]]]
    support_roles: NotRequired[list[MonsterRole]]


MONSTER_ENCOUNTER_PROFILES: dict[str, dict[EncounterKind, dict[EncounterDifficulty, MonsterEncounterProfile]]] = {
    "rat_swarm": {
        "ordinary": {
            "easy": {
                "budget_multiplier": 0.75,
                "min_units": 3,
                "max_units": 6,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": [],
                "role_caps": {"minion": 6, "veteran": 6, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.0,
                "min_units": 3,
                "max_units": 6,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 6, "veteran": 6, "elite": 2, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.25,
                "min_units": 3,
                "max_units": 6,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 0, "veteran": 6, "elite": 3, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "guard": {
            "easy": {
                "budget_multiplier": 0.85,
                "min_units": 3,
                "max_units": 6,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 6, "veteran": 3, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.1,
                "min_units": 3,
                "max_units": 6,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 6, "veteran": 6, "elite": 2, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.3,
                "min_units": 3,
                "max_units": 6,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["elite"],
                "role_caps": {"minion": 0, "veteran": 6, "elite": 3, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "boss": {
            "easy": {
                "budget_multiplier": 1.0,
                "min_units": 2,
                "max_units": 4,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["veteran", "elite"],
                "role_caps": {"minion": 0, "veteran": 3, "elite": 1, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.2,
                "min_units": 3,
                "max_units": 5,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 5, "veteran": 4, "elite": 1, "boss": 1},
                "upgrade_order": ["veteran", "elite", "boss"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.45,
                "min_units": 4,
                "max_units": 6,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 0, "veteran": 6, "elite": 2, "boss": 1},
                "upgrade_order": ["elite", "boss"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
    },
    "goblin_tribe": {
        "ordinary": {
            "easy": {
                "budget_multiplier": 0.75,
                "min_units": 2,
                "max_units": 5,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": [],
                "role_caps": {"minion": 5, "veteran": 5, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.0,
                "min_units": 2,
                "max_units": 5,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 5, "veteran": 5, "elite": 1, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.25,
                "min_units": 2,
                "max_units": 5,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 0, "veteran": 5, "elite": 2, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "guard": {
            "easy": {
                "budget_multiplier": 0.85,
                "min_units": 2,
                "max_units": 4,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 4, "veteran": 2, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.1,
                "min_units": 2,
                "max_units": 5,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 5, "veteran": 5, "elite": 1, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.3,
                "min_units": 3,
                "max_units": 5,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["elite"],
                "role_caps": {"minion": 0, "veteran": 5, "elite": 2, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "boss": {
            "easy": {
                "budget_multiplier": 1.0,
                "min_units": 2,
                "max_units": 3,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["veteran", "elite"],
                "role_caps": {"minion": 0, "veteran": 2, "elite": 1, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.2,
                "min_units": 2,
                "max_units": 4,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 4, "veteran": 3, "elite": 1, "boss": 1},
                "upgrade_order": ["veteran", "elite", "boss"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.45,
                "min_units": 3,
                "max_units": 5,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 0, "veteran": 5, "elite": 2, "boss": 1},
                "upgrade_order": ["elite", "boss"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
    },
    "wolf_pack": {
        "ordinary": {
            "easy": {
                "budget_multiplier": 0.75,
                "min_units": 2,
                "max_units": 4,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": [],
                "role_caps": {"minion": 4, "veteran": 4, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.0,
                "min_units": 2,
                "max_units": 4,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 4, "veteran": 4, "elite": 1, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.25,
                "min_units": 2,
                "max_units": 4,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 0, "veteran": 4, "elite": 2, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "guard": {
            "easy": {
                "budget_multiplier": 0.85,
                "min_units": 2,
                "max_units": 3,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 3, "veteran": 2, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.1,
                "min_units": 2,
                "max_units": 4,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 4, "veteran": 4, "elite": 1, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.3,
                "min_units": 2,
                "max_units": 4,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["elite"],
                "role_caps": {"minion": 0, "veteran": 4, "elite": 2, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "boss": {
            "easy": {
                "budget_multiplier": 1.0,
                "min_units": 2,
                "max_units": 3,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["veteran", "elite"],
                "role_caps": {"minion": 0, "veteran": 2, "elite": 1, "boss": 0},
                "upgrade_order": ["elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "budget_multiplier": 1.2,
                "min_units": 2,
                "max_units": 4,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 4, "veteran": 3, "elite": 1, "boss": 1},
                "upgrade_order": ["veteran", "elite", "boss"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "budget_multiplier": 1.45,
                "min_units": 3,
                "max_units": 4,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 0, "veteran": 4, "elite": 2, "boss": 1},
                "upgrade_order": ["elite", "boss"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
    },
    "bandit_gang": {
        "ordinary": {
            "easy": {
                "build_mode": "upgrade_ladder",
                "budget_multiplier": 0.75,
                "min_units": 1,
                "max_units": 3,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": [],
                "role_caps": {"minion": 3, "veteran": 3, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "upgrade_stages": [{"role": "veteran", "requires": {"minion": 3}}],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "build_mode": "upgrade_ladder",
                "budget_multiplier": 1.0,
                "min_units": 1,
                "max_units": 3,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 3, "veteran": 3, "elite": 1, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "upgrade_stages": [
                    {"role": "veteran", "requires": {"minion": 3}},
                    {"role": "elite", "requires": {"veteran": 3}},
                ],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "build_mode": "upgrade_ladder",
                "budget_multiplier": 1.25,
                "min_units": 2,
                "max_units": 3,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": [],
                "role_caps": {"minion": 0, "veteran": 3, "elite": 2, "boss": 0},
                "upgrade_order": ["elite"],
                "upgrade_stages": [{"role": "elite", "requires": {"veteran": 1}}],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "guard": {
            "easy": {
                "build_mode": "anchor_and_support",
                "budget_multiplier": 0.85,
                "min_units": 1,
                "max_units": 3,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 3, "veteran": 2, "elite": 0, "boss": 0},
                "upgrade_order": ["veteran"],
                "support_roles": ["minion"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "build_mode": "anchor_and_support",
                "budget_multiplier": 1.1,
                "min_units": 2,
                "max_units": 3,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite"],
                "required_roles": ["veteran"],
                "role_caps": {"minion": 3, "veteran": 3, "elite": 1, "boss": 0},
                "upgrade_order": ["veteran", "elite"],
                "support_roles": ["minion", "veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "build_mode": "anchor_and_support",
                "budget_multiplier": 1.3,
                "min_units": 2,
                "max_units": 3,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["elite"],
                "role_caps": {"minion": 0, "veteran": 3, "elite": 2, "boss": 0},
                "upgrade_order": ["elite"],
                "support_roles": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
        "boss": {
            "easy": {
                "build_mode": "anchor_and_support",
                "budget_multiplier": 1.0,
                "min_units": 2,
                "max_units": 3,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite"],
                "required_roles": ["veteran", "elite"],
                "role_caps": {"minion": 0, "veteran": 2, "elite": 1, "boss": 0},
                "upgrade_order": ["elite"],
                "support_roles": ["veteran"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "normal": {
                "build_mode": "anchor_and_support",
                "budget_multiplier": 1.2,
                "min_units": 2,
                "max_units": 3,
                "start_role": "minion",
                "allowed_roles": ["minion", "veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 3, "veteran": 2, "elite": 1, "boss": 1},
                "upgrade_order": ["veteran", "elite", "boss"],
                "support_roles": ["minion", "veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
            "hard": {
                "build_mode": "anchor_and_support",
                "budget_multiplier": 1.45,
                "min_units": 2,
                "max_units": 3,
                "start_role": "veteran",
                "allowed_roles": ["veteran", "elite", "boss"],
                "required_roles": ["boss"],
                "role_caps": {"minion": 0, "veteran": 3, "elite": 2, "boss": 1},
                "upgrade_order": ["elite", "boss"],
                "support_roles": ["veteran", "elite"],
                "allow_repeated_members": True,
                "prefer_distinct_members": True,
            },
        },
    },
}


def get_monster_encounter_profile(
    family_id: str,
    kind: EncounterKind,
    difficulty: EncounterDifficulty,
) -> MonsterEncounterProfile | None:
    family_profiles = MONSTER_ENCOUNTER_PROFILES.get(family_id)
    if family_profiles is None:
        return None
    kind_profiles = family_profiles.get(kind)
    if kind_profiles is None:
        return None
    profile = kind_profiles.get(difficulty)
    if profile is None:
        return None
    return cast(
        "MonsterEncounterProfile",
        _with_default_build_contract(cast("dict[str, Any]", deepcopy(profile)), kind=kind, difficulty=difficulty),
    )


def _with_default_build_contract(
    profile: dict[str, Any],
    *,
    kind: EncounterKind,
    difficulty: EncounterDifficulty,
) -> dict[str, Any]:
    if kind == "ordinary":
        profile.setdefault("build_mode", "upgrade_ladder")
        profile.setdefault("upgrade_stages", _ordinary_upgrade_stages(profile, difficulty=difficulty))
        return profile

    profile.setdefault("build_mode", "anchor_and_support")
    profile.setdefault("support_roles", _anchor_support_roles(profile))
    return profile


def _ordinary_upgrade_stages(profile: dict[str, Any], *, difficulty: EncounterDifficulty) -> list[dict[str, Any]]:
    max_units = _positive_int(profile.get("max_units"), default=1)
    min_units = _positive_int(profile.get("min_units"), default=1)
    start_role = str(profile.get("start_role") or "minion")
    stages: list[dict[str, Any]] = []
    if "veteran" in _strings(profile.get("upgrade_order")) and start_role == "minion":
        stages.append({"role": "veteran", "requires": {"minion": max_units}})
    if "elite" in _strings(profile.get("upgrade_order")):
        required_veterans = max_units if difficulty == "normal" and start_role == "minion" else min_units
        stages.append({"role": "elite", "requires": {"veteran": required_veterans}})
    return stages


def _anchor_support_roles(profile: dict[str, Any]) -> list[str]:
    allowed_roles = _strings(profile.get("allowed_roles"))
    required_roles = set(_strings(profile.get("required_roles")))
    return [role for role in allowed_roles if role not in required_roles]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return []


def _positive_int(value: Any, *, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


__all__ = [
    "EncounterDifficulty",
    "EncounterKind",
    "MONSTER_ENCOUNTER_PROFILES",
    "MonsterEncounterProfile",
    "MonsterRole",
    "get_monster_encounter_profile",
]
