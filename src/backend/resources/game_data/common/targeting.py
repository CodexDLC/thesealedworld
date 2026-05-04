from enum import Enum


class TargetType(str, Enum):
    SELF = "self"
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"
    RANDOM_ENEMY = "random_enemy"
    LOWEST_HP_ALLY = "lowest_hp_ally"
    LOWEST_HP_ENEMY = "lowest_hp_enemy"
    CLEAVE = "cleave"  # Атака по 3 целям
