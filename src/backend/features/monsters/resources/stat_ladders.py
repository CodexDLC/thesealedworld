from __future__ import annotations

from typing import Final, Literal

MonsterRole = Literal["minion", "veteran", "elite", "boss"]
MonsterOrganizationType = Literal["solitary", "pack", "gang", "horde", "swarm"]

ATTRIBUTE_KEYS: Final[tuple[str, ...]] = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
)

ATTRIBUTE_LADDER: Final[tuple[int, ...]] = (9, 8, 7, 6, 5, 4, 3, 2, 1)

PLAYER_ATTRIBUTE_BASE: Final[int] = 8

ROLE_ATTRIBUTE_OFFSETS: Final[dict[MonsterRole, int]] = {
    "minion": -3,
    "veteran": -2,
    "elite": -1,
    "boss": 4,
}

ROLE_ATTRIBUTE_BASE: Final[dict[MonsterRole, int]] = {
    role: PLAYER_ATTRIBUTE_BASE + offset for role, offset in ROLE_ATTRIBUTE_OFFSETS.items()
}

ORGANIZATION_ATTRIBUTE_OFFSETS: Final[dict[MonsterOrganizationType, int]] = {
    "swarm": -2,
    "horde": -1,
    "pack": 0,
    "gang": 1,
    "solitary": 2,
}


def role_attribute_base(role: MonsterRole, organization_type: MonsterOrganizationType = "pack") -> int:
    if role == "boss":
        return ROLE_ATTRIBUTE_BASE[role]
    return ROLE_ATTRIBUTE_BASE[role] + ORGANIZATION_ATTRIBUTE_OFFSETS[organization_type]


def build_role_ladder_stats(
    role: MonsterRole,
    priority: tuple[str, ...],
    *,
    organization_type: MonsterOrganizationType = "pack",
) -> dict[str, int]:
    unknown = sorted(set(priority) - set(ATTRIBUTE_KEYS))
    if unknown:
        raise ValueError(f"Unknown monster attribute keys: {unknown}")

    order = list(dict.fromkeys(priority))
    order.extend(key for key in ATTRIBUTE_KEYS if key not in order)
    if len(order) != len(ATTRIBUTE_KEYS):
        raise ValueError("Monster attribute ladder must cover the full attribute contract")

    base = role_attribute_base(role, organization_type)
    return {key: base + bonus for key, bonus in zip(order, ATTRIBUTE_LADDER, strict=True)}
