from __future__ import annotations

from typing import Any

from src.backend.features.game_catalog.skills.resources.contracts import ACTOR_SNAPSHOT_SKILL_KEYS

MONSTER_COMBAT_SKILL_KEYS: frozenset[str] = frozenset(
    key for key in ACTOR_SNAPSHOT_SKILL_KEYS if key != "skill_adaptation"
)


def filter_monster_combat_skills(raw: dict[str, Any]) -> dict[str, float]:
    skills = raw.get("skills") if isinstance(raw, dict) and "skills" in raw else raw
    if not isinstance(skills, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in skills.items():
        skill_key = str(key)
        if skill_key not in MONSTER_COMBAT_SKILL_KEYS:
            continue
        try:
            result[skill_key] = round(float(value or 0.0), 4)
        except (TypeError, ValueError):
            result[skill_key] = 0.0
    return result


__all__ = ["MONSTER_COMBAT_SKILL_KEYS", "filter_monster_combat_skills"]
