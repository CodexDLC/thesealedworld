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


def _body_average_rules(multiplier: float) -> dict[str, float]:
    per_attribute = multiplier / 3.0
    return {
        StatKey.STRENGTH: per_attribute,
        StatKey.AGILITY: per_attribute,
        StatKey.ENDURANCE: per_attribute,
    }


def _player_rules(
    rules: dict[str, dict[str, float]], *, body_hp_multiplier: float, body_hp_regen_multiplier: float
) -> dict[str, dict[str, float]]:
    profile = {target: dict(sources) for target, sources in rules.items()}
    profile[StatKey.HP] = _body_average_rules(body_hp_multiplier)
    profile[StatKey.HP_REGEN] = _body_average_rules(body_hp_regen_multiplier)
    return profile


def _monster_rules(rules: dict[str, dict[str, float]], *, body_hp_multiplier: float) -> dict[str, dict[str, float]]:
    profile = _without_hp_regen(rules)
    profile[StatKey.HP] = _body_average_rules(body_hp_multiplier)
    return profile


PLAYER_NAKED_ATTRIBUTE_RULES = _player_rules(
    ATTRIBUTE_MODIFIER_RULES, body_hp_multiplier=3.0, body_hp_regen_multiplier=0.05
)
PLAYER_LIGHT_ATTRIBUTE_RULES = _player_rules(
    ATTRIBUTE_MODIFIER_RULES, body_hp_multiplier=4.0, body_hp_regen_multiplier=0.10
)
PLAYER_MEDIUM_ATTRIBUTE_RULES = _player_rules(
    ATTRIBUTE_MODIFIER_RULES, body_hp_multiplier=5.0, body_hp_regen_multiplier=0.10
)
PLAYER_HEAVY_ATTRIBUTE_RULES = _player_rules(
    ATTRIBUTE_MODIFIER_RULES, body_hp_multiplier=6.0, body_hp_regen_multiplier=0.20
)
PLAYER_ATTRIBUTE_RULES = PLAYER_NAKED_ATTRIBUTE_RULES
MONSTER_HUMANOID_ATTRIBUTE_RULES = _monster_rules(ATTRIBUTE_MODIFIER_RULES, body_hp_multiplier=3.0)
MONSTER_BEAST_ATTRIBUTE_RULES = _monster_rules(ATTRIBUTE_MODIFIER_RULES, body_hp_multiplier=5.0)

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
