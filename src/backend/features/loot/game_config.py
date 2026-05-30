from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class LootConfig(BaseGameConfig):
    namespace = "loot"

    config_metadata = {
        "PUBLIC_DELAY_SEC": ConfigEntryMeta(
            label="Задержка публичности",
            description="Время (в секундах) до того как персональный лут становится публичным.",
            group="Таймеры лута",
            unit="seconds",
            min_value=0.0,
            max_value=3600.0,
            step=60.0,
            risk="medium",
            tags=("loot", "timer"),
        ),
        "PUBLIC_WINDOW_SEC": ConfigEntryMeta(
            label="Окно публичности",
            description="Время (в секундах), в течение которого публичный лут доступен для всех.",
            group="Таймеры лута",
            unit="seconds",
            min_value=0.0,
            max_value=7200.0,
            step=60.0,
            risk="medium",
            tags=("loot", "timer"),
        ),
        "INVISIBLE_TTL_SEC": ConfigEntryMeta(
            label="Время жизни невидимого трупа",
            description="TTL невидимого трупа (в секундах).",
            group="Таймеры лута",
            unit="seconds",
            min_value=3600.0,
            max_value=172800.0,
            step=3600.0,
            risk="low",
            tags=("loot", "timer", "ttl"),
        ),
        "EMPTY_CORPSE_TTL_SEC": ConfigEntryMeta(
            label="Время жизни пустого трупа",
            description="TTL пустого трупа (в секундах).",
            group="Таймеры лута",
            unit="seconds",
            min_value=0.0,
            max_value=3600.0,
            step=60.0,
            risk="low",
            tags=("loot", "timer", "ttl"),
        ),
    }

    PUBLIC_DELAY_SEC = 900.0
    PUBLIC_WINDOW_SEC = 3600.0
    INVISIBLE_TTL_SEC = 86400.0
    EMPTY_CORPSE_TTL_SEC = 300.0

    TIER_WEIGHT_COMMON = 60
    TIER_WEIGHT_UNCOMMON = 25
    TIER_WEIGHT_RARE = 10
    TIER_WEIGHT_EPIC = 4
    TIER_WEIGHT_LEGENDARY = 1
