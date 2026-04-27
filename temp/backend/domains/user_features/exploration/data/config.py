# backend/domains/user_features/exploration/data/config.py


class ExplorationConfig:
    """
    Конфигурация и балансные константы домена Exploration.
    """

    # --- World Constants ---
    DEFAULT_SPAWN_POINT = "52_52"  # Стартовая локация (Fallback)

    # --- Encounter Chances (Global) ---
    CHANCE_MERCHANT = 0.01  # 1%
    CHANCE_QUEST = 0.02  # 2%
    CHANCE_COMBAT_BASE = 0.45  # 45%
    CHANCE_COMBAT_SEARCH = 0.80  # 80% при поиске

    # --- Combat Difficulty Weights (by Tier) ---
    # {tier: {difficulty: weight}}
    # Сумма весов должна быть равна 100 (или будет нормализована)
    TIER_DIFFICULTY_WEIGHTS = {
        0: {"easy": 100, "mid": 0, "hard": 0},
        1: {"easy": 80, "mid": 15, "hard": 5},
        2: {"easy": 70, "mid": 20, "hard": 10},
        3: {"easy": 50, "mid": 35, "hard": 15},
        4: {"easy": 40, "mid": 40, "hard": 20},
        5: {"easy": 30, "mid": 40, "hard": 30},
        6: {"easy": 20, "mid": 40, "hard": 40},
        7: {"easy": 10, "mid": 30, "hard": 60},  # Hell
    }

    # --- Detection Modifiers ---
    # Насколько сложнее заметить врага определенного ранга
    DETECTION_MODIFIERS = {"easy": 0, "mid": 10, "hard": 20}
