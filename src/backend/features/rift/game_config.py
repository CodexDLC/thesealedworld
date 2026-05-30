from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class RiftConfig(BaseGameConfig):
    namespace = "rift"

    # Transition travel / combat pacing
    TRANSITION_BASE_CHANCE_PER_TICK: float = 0.35
    TRANSITION_TICK_INTERVAL_MS: int = 1000
    TRANSITION_EXPLORATION_DURATION_MS: int = 3000
    TRANSITION_RETURN_DURATION_MS: int = 1000
    TRANSITION_SUPPRESS_ORDINARY_AFTER_COMBAT: bool = True

    # Ordinary node combat
    ORDINARY_NODE_COMBAT_ENABLED: bool = True
    ORDINARY_NODE_FIRST_VISIT_ONLY: bool = True
    ORDINARY_NODE_COMBAT_CHANCE: float = 0.30

    config_metadata = {
        "TRANSITION_BASE_CHANCE_PER_TICK": ConfigEntryMeta(
            label="Шанс боя при переходе",
            description="Вероятность transition combat на один travel tick в рифте.",
            group="Rift combat pacing",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="high",
            live_scope="new_travel_tick",
            tags=("rift", "combat", "encounter", "balance"),
        ),
        "TRANSITION_TICK_INTERVAL_MS": ConfigEntryMeta(
            label="Интервал travel tick",
            description="Размер одного transition tick при движении между узлами рифта.",
            group="Rift travel pacing",
            unit="milliseconds",
            min_value=100.0,
            max_value=60000.0,
            step=100.0,
            risk="medium",
            live_scope="new_travel",
            tags=("rift", "travel", "pacing"),
        ),
        "TRANSITION_EXPLORATION_DURATION_MS": ConfigEntryMeta(
            label="Длительность движения вперед",
            description="Базовая длительность движения к непосещенному узлу рифта.",
            group="Rift travel pacing",
            unit="milliseconds",
            min_value=0.0,
            max_value=300000.0,
            step=100.0,
            risk="medium",
            live_scope="new_travel",
            tags=("rift", "travel", "pacing"),
        ),
        "TRANSITION_RETURN_DURATION_MS": ConfigEntryMeta(
            label="Длительность возврата",
            description="Базовая длительность возврата к посещенному узлу рифта.",
            group="Rift travel pacing",
            unit="milliseconds",
            min_value=0.0,
            max_value=300000.0,
            step=100.0,
            risk="medium",
            live_scope="new_travel",
            tags=("rift", "travel", "pacing"),
        ),
        "TRANSITION_SUPPRESS_ORDINARY_AFTER_COMBAT": ConfigEntryMeta(
            label="Подавлять ordinary combat после transition combat",
            description="Если transition combat уже сработал, не роллить ordinary node combat на целевом узле.",
            group="Rift combat pacing",
            unit="flag",
            risk="medium",
            live_scope="travel_resolution",
            tags=("rift", "combat", "encounter"),
        ),
        "ORDINARY_NODE_COMBAT_ENABLED": ConfigEntryMeta(
            label="Ordinary node combat включен",
            description="Глобально включает случайный ordinary combat при входе на обычный узел рифта.",
            group="Rift combat pacing",
            unit="flag",
            risk="high",
            live_scope="node_entry",
            tags=("rift", "combat", "encounter"),
        ),
        "ORDINARY_NODE_FIRST_VISIT_ONLY": ConfigEntryMeta(
            label="Ordinary combat только на первом визите",
            description="Запрещает повторный roll ordinary combat на уже посещенном узле.",
            group="Rift combat pacing",
            unit="flag",
            risk="medium",
            live_scope="node_entry",
            tags=("rift", "combat", "encounter"),
        ),
        "ORDINARY_NODE_COMBAT_CHANCE": ConfigEntryMeta(
            label="Шанс ordinary node combat",
            description="Вероятность случайного боя при входе на обычный узел рифта.",
            group="Rift combat pacing",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="high",
            live_scope="node_entry",
            tags=("rift", "combat", "encounter", "balance"),
        ),
    }
