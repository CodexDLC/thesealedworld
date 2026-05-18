from __future__ import annotations

from src.backend.features.character.runtime.rules.attribute_modifiers import ATTRIBUTE_MODIFIER_RULES
from src.shared.enums.stats_enums import StatKey

PLAYER_ATTRIBUTE_RULES = ATTRIBUTE_MODIFIER_RULES


def _without_hp_regen(rules: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    return {target: dict(sources) for target, sources in rules.items() if target != StatKey.HP_REGEN}


MONSTER_HUMANOID_ATTRIBUTE_RULES = _without_hp_regen(ATTRIBUTE_MODIFIER_RULES)
MONSTER_BEAST_ATTRIBUTE_RULES = _without_hp_regen(ATTRIBUTE_MODIFIER_RULES)

ATTRIBUTE_RULE_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "player": PLAYER_ATTRIBUTE_RULES,
    "monster:humanoid": MONSTER_HUMANOID_ATTRIBUTE_RULES,
    "monster:beast": MONSTER_BEAST_ATTRIBUTE_RULES,
}


def resolve_attribute_rules(profile_key: str | None) -> dict[str, dict[str, float]]:
    return ATTRIBUTE_RULE_PROFILES.get(str(profile_key or "player"), PLAYER_ATTRIBUTE_RULES)


__all__ = [
    "ATTRIBUTE_RULE_PROFILES",
    "MONSTER_BEAST_ATTRIBUTE_RULES",
    "MONSTER_HUMANOID_ATTRIBUTE_RULES",
    "PLAYER_ATTRIBUTE_RULES",
    "resolve_attribute_rules",
]
