from src.backend.infrastructure.game_config.base import BaseGameConfig


class CombatConfig(BaseGameConfig):
    namespace = "combat"

    # Parry / Block
    PARRY_SKILL_MULT_PER_POINT: float = 4.0
    SHIELD_BLOCK_SKILL_MULT_PER_POINT: float = 1.5
    SHIELD_MASTERY_ABSORB_RATIO_PER_POINT: float = 0.20
    SHIELD_ABSORB_RATIO_CAP: float = 0.85

    # Unarmed combat
    UNARMED_MIN_EFFICIENCY: float = 0.5
    UNARMED_MAX_EFFICIENCY: float = 3.0
    UNARMED_NOVICE_SPREAD: float = 0.5
    UNARMED_MASTER_SPREAD: float = 0.1

    # Chaos system
    CHAOS_FIRST_CHECK_DELAY_SECONDS: int = 300
    SESSION_TTL_SECONDS: int = 3600
