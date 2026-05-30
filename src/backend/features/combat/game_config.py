from src.backend.infrastructure.game_config.base import BaseGameConfig


class CombatConfig(BaseGameConfig):
    namespace = "combat"

    # Parry / Block
    PARRY_SKILL_MULT_PER_POINT: float = 4.0
    SHIELD_BLOCK_SKILL_BONUS_AT_FULL: float = 0.32
    SHIELD_MASTERY_ABSORB_CAP_RATIO_AT_FULL: float = 0.50
    SHIELD_MASTERY_REFLECT_RATIO_AT_FULL: float = 1.00

    # Accuracy
    BASE_ACCURACY_CHANCE: float = 0.70
    SKILL_ACCURACY_BONUS_AT_FULL: float = 0.30
    ACCURACY_CHANCE_CAP: float = 0.90
    ACCURACY_PENALTY_WEAPON_SKILL_REDUCTION_AT_FULL: float = 0.45
    ACCURACY_PENALTY_STYLE_SKILL_REDUCTION_AT_FULL: float = 0.45
    ACCURACY_PENALTY_MIN_MULTIPLIER: float = 0.10

    # Tokens
    TOKEN_BONUS_CHANCE: float = 0.30

    # Unarmed combat
    UNARMED_MIN_EFFICIENCY: float = 0.5
    UNARMED_MAX_EFFICIENCY: float = 3.0
    UNARMED_NOVICE_SPREAD: float = 0.5
    UNARMED_MASTER_SPREAD: float = 0.1

    # Chaos system
    CHAOS_FIRST_CHECK_DELAY_SECONDS: int = 300
    SESSION_TTL_SECONDS: int = 3600
