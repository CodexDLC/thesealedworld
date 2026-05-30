from typing import ClassVar

from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


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

    config_metadata = {
        "DEFAULT_SPAWN_POINT": ConfigEntryMeta(
            label="Стартовая точка",
            description="Fallback location id для персонажа, если активная позиция отсутствует.",
            group="Мир",
            unit="location_id",
            risk="high",
            live_scope="next_location_resolution",
            tags=("exploration", "world"),
        ),
        "TRAVEL_TIME_MULT": ConfigEntryMeta(
            label="Множитель времени путешествия",
            description="Глобально ускоряет или замедляет travel pacing.",
            group="Темп путешествий",
            unit="multiplier",
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            risk="medium",
            live_scope="new_travel",
            tags=("exploration", "pacing"),
        ),
        "EVENT_CHANCE_PER_STEP": ConfigEntryMeta(
            label="Шанс события на шаг",
            description="Базовая вероятность получить exploration event на шаг перемещения.",
            group="Темп путешествий",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_step",
            tags=("exploration", "events"),
        ),
        "CHANCE_MERCHANT": ConfigEntryMeta(
            label="Шанс торговца",
            description="Зарезервированный шанс merchant discovery в exploration policy.",
            group="Энкаунтеры",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="low",
            live_scope="reserved",
            tags=("exploration", "encounter", "reserved"),
        ),
        "CHANCE_QUEST": ConfigEntryMeta(
            label="Шанс квеста",
            description="Зарезервированный шанс quest discovery в exploration policy.",
            group="Энкаунтеры",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="low",
            live_scope="reserved",
            tags=("exploration", "encounter", "reserved"),
        ),
        "CHANCE_COMBAT_BASE": ConfigEntryMeta(
            label="Базовый шанс боя",
            description="Вероятность combat encounter при обычном travel roll.",
            group="Энкаунтеры",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="high",
            live_scope="next_encounter_roll",
            tags=("exploration", "encounter", "combat"),
        ),
        "CHANCE_COMBAT_SEARCH": ConfigEntryMeta(
            label="Шанс боя при поиске",
            description="Вероятность combat encounter, когда игрок явно ищет столкновение.",
            group="Энкаунтеры",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="high",
            live_scope="next_encounter_roll",
            tags=("exploration", "encounter", "combat"),
        ),
        "ENCOUNTER_BASE_CHANCE": ConfigEntryMeta(
            label="Базовый шанс discovery",
            description="Зарезервированная базовая вероятность discovery engine.",
            group="Энкаунтеры",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="reserved",
            tags=("exploration", "encounter", "reserved"),
        ),
        "ENCOUNTER_WEIGHT_BASE": ConfigEntryMeta(
            label="Базовый вес энкаунтера",
            description="Зарезервированный multiplier для весов encounter selection.",
            group="Энкаунтеры",
            unit="weight",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            risk="medium",
            live_scope="reserved",
            tags=("exploration", "encounter", "reserved"),
        ),
        "ENCOUNTER_SESSION_TTL_SECONDS": ConfigEntryMeta(
            label="Время жизни энкаунтера",
            description="TTL Redis-сессии exploration encounter. 1800 = 30 минут.",
            group="Сессии",
            unit="seconds",
            min_value=60.0,
            max_value=86400.0,
            step=60.0,
            risk="medium",
            live_scope="new_encounter_session",
            tags=("exploration", "runtime", "ttl"),
        ),
    }

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
