from __future__ import annotations

from src.backend.features.character.runtime.rules.attribute_modifiers import ATTRIBUTE_MODIFIER_RULES
from src.backend.features.character.runtime.vital_profile import (
    PLAYER_VITAL_PROFILE_HEAVY,
    PLAYER_VITAL_PROFILE_LIGHT,
    PLAYER_VITAL_PROFILE_MEDIUM,
    PLAYER_VITAL_PROFILE_NAKED,
)
from src.shared.enums.stats_enums import StatKey


def _without_hp_regen(rules: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    return {target: dict(sources) for target, sources in rules.items() if target != StatKey.HP_REGEN}


def _player_rules(
    rules: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    profile = {target: dict(sources) for target, sources in rules.items()}
    return profile


def _monster_rules(rules: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    profile = _without_hp_regen(rules)
    profile[StatKey.HP] = {StatKey.ENDURANCE: 3.0}
    return profile


PLAYER_NAKED_ATTRIBUTE_RULES = _player_rules(ATTRIBUTE_MODIFIER_RULES)
PLAYER_LIGHT_ATTRIBUTE_RULES = _player_rules(ATTRIBUTE_MODIFIER_RULES)
PLAYER_MEDIUM_ATTRIBUTE_RULES = _player_rules(ATTRIBUTE_MODIFIER_RULES)
PLAYER_HEAVY_ATTRIBUTE_RULES = _player_rules(ATTRIBUTE_MODIFIER_RULES)
PLAYER_ATTRIBUTE_RULES = PLAYER_NAKED_ATTRIBUTE_RULES
MONSTER_HUMANOID_ATTRIBUTE_RULES = _monster_rules(ATTRIBUTE_MODIFIER_RULES)
MONSTER_BEAST_ATTRIBUTE_RULES = _monster_rules(ATTRIBUTE_MODIFIER_RULES)

ATTRIBUTE_RULE_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "player": PLAYER_ATTRIBUTE_RULES,
    PLAYER_VITAL_PROFILE_NAKED: PLAYER_NAKED_ATTRIBUTE_RULES,
    PLAYER_VITAL_PROFILE_LIGHT: PLAYER_LIGHT_ATTRIBUTE_RULES,
    PLAYER_VITAL_PROFILE_MEDIUM: PLAYER_MEDIUM_ATTRIBUTE_RULES,
    PLAYER_VITAL_PROFILE_HEAVY: PLAYER_HEAVY_ATTRIBUTE_RULES,
    "monster:humanoid": MONSTER_HUMANOID_ATTRIBUTE_RULES,
    "monster:beast": MONSTER_BEAST_ATTRIBUTE_RULES,
}


def resolve_attribute_rules(profile_key: str | None) -> dict[str, dict[str, float]]:
    return ATTRIBUTE_RULE_PROFILES.get(str(profile_key or "player"), PLAYER_ATTRIBUTE_RULES)


__all__ = [
    "ATTRIBUTE_RULE_PROFILES",
    "MONSTER_BEAST_ATTRIBUTE_RULES",
    "MONSTER_HUMANOID_ATTRIBUTE_RULES",
    "PLAYER_HEAVY_ATTRIBUTE_RULES",
    "PLAYER_LIGHT_ATTRIBUTE_RULES",
    "PLAYER_MEDIUM_ATTRIBUTE_RULES",
    "PLAYER_NAKED_ATTRIBUTE_RULES",
    "PLAYER_ATTRIBUTE_RULES",
    "resolve_attribute_rules",
]
