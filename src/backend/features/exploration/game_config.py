from typing import ClassVar

from src.backend.infrastructure.game_config.base import BaseGameConfig


class ExplorationConfig(BaseGameConfig):
    namespace = "exploration"

    # ── World ──────────────────────────────────────────────────────────────────
    DEFAULT_SPAWN_POINT: str = "52_52"

    # ── Travel / event pacing ──────────────────────────────────────────────────
    TRAVEL_TIME_MULT: float = 1.0
    EVENT_CHANCE_PER_STEP: float = 0.08

    # ── Encounter chances (global) ─────────────────────────────────────────────
    CHANCE_MERCHANT: float = 0.01
    CHANCE_QUEST: float = 0.02
    CHANCE_COMBAT_BASE: float = 0.45
    CHANCE_COMBAT_SEARCH: float = 0.80
    ENCOUNTER_BASE_CHANCE: float = 0.15
    ENCOUNTER_WEIGHT_BASE: float = 1.0

    # ── Session lifetime ───────────────────────────────────────────────────────
    ENCOUNTER_SESSION_TTL_SECONDS: int = 30 * 60

    # ── Tables (non-scalar, not Redis-overridable) ─────────────────────────────
    # BaseGameConfig.defaults() filters to scalar types only, so these dict
    # constants are deliberately excluded from the cabinet UI for now.
    # They remain class-level attributes for direct reuse from runtime code.
    TIER_DIFFICULTY_WEIGHTS: ClassVar[dict[int, dict[str, int]]] = {
        0: {"easy": 100, "mid": 0, "hard": 0},
        1: {"easy": 80, "mid": 15, "hard": 5},
        2: {"easy": 70, "mid": 20, "hard": 10},
        3: {"easy": 50, "mid": 35, "hard": 15},
        4: {"easy": 40, "mid": 40, "hard": 20},
        5: {"easy": 30, "mid": 40, "hard": 30},
        6: {"easy": 20, "mid": 40, "hard": 40},
        7: {"easy": 10, "mid": 30, "hard": 60},  # Hell
    }
    DETECTION_MODIFIERS: ClassVar[dict[str, int]] = {"easy": 0, "mid": 10, "hard": 20}
