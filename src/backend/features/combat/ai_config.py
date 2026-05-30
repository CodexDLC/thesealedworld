"""Cabinet-exposed AI/training settings for combat.

Kept separate from ``CombatConfig`` (combat math) so admins can clearly
distinguish balance knobs from AI training/policy knobs in the cabinet UI.
"""

from src.backend.infrastructure.game_config.base import BaseGameConfig


class CombatAiConfig(BaseGameConfig):
    namespace = "combat_ai"

    # Active policy id for newly created combat sessions. In live combat this is
    # first resolved as a completed training run id with metadata.best_policy;
    # legacy bundled policy ids still fall back through PolicyStore.
    ACTIVE_POLICY_ID: str = ""

    # Multiplier applied to the policy's ``randomness`` weight at runtime.
    # 1.0 = use the weight as-trained; 0.0 = fully deterministic.
    EXPLORATION_RANDOMNESS_MULT: float = 1.0

    # Feature flag for online training entry points. Off in prod by default.
    TRAINING_ENABLED: bool = False

    # Deterministic seed for training scripts. 0 = derive from system entropy.
    TRAINING_SEED: int = 0
