from __future__ import annotations

from typing import Final, Literal

MonsterRole = Literal["minion", "veteran", "elite", "boss"]

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

ROLE_ATTRIBUTE_BASE: Final[dict[MonsterRole, int]] = {
    "minion": 4,
    "veteran": 6,
    "elite": 8,
    "boss": 12,
}


def build_role_ladder_stats(role: MonsterRole, priority: tuple[str, ...]) -> dict[str, int]:
    unknown = sorted(set(priority) - set(ATTRIBUTE_KEYS))
    if unknown:
        raise ValueError(f"Unknown monster attribute keys: {unknown}")

    order = list(dict.fromkeys(priority))
    order.extend(key for key in ATTRIBUTE_KEYS if key not in order)
    if len(order) != len(ATTRIBUTE_KEYS):
        raise ValueError("Monster attribute ladder must cover the full attribute contract")

    base = ROLE_ATTRIBUTE_BASE[role]
    return {key: base + bonus for key, bonus in zip(order, ATTRIBUTE_LADDER, strict=True)}
