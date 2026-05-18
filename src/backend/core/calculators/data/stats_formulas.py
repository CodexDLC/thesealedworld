from src.backend.core.calculators.data.attribute_rule_profiles import (
    ATTRIBUTE_RULE_PROFILES,
    MONSTER_BEAST_ATTRIBUTE_RULES,
    MONSTER_HUMANOID_ATTRIBUTE_RULES,
    PLAYER_ATTRIBUTE_RULES,
    resolve_attribute_rules,
)
from src.backend.features.character.runtime.rules.attribute_modifiers import (
    ATTRIBUTE_MODIFIER_RULES,
    DEFAULT_MODIFIER_VALUES,
    MODIFIER_RULES,
)

DEFAULT_VALUES = DEFAULT_MODIFIER_VALUES

__all__ = [
    "ATTRIBUTE_MODIFIER_RULES",
    "ATTRIBUTE_RULE_PROFILES",
    "DEFAULT_MODIFIER_VALUES",
    "DEFAULT_VALUES",
    "MODIFIER_RULES",
    "MONSTER_BEAST_ATTRIBUTE_RULES",
    "MONSTER_HUMANOID_ATTRIBUTE_RULES",
    "PLAYER_ATTRIBUTE_RULES",
    "resolve_attribute_rules",
]
