from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class LootConfig(BaseGameConfig):
    namespace = "loot"

    # Redis EXPIRE requires integer seconds — keep these as int to avoid
    # "value is not an integer or out of range" errors from the Redis wire protocol.
    PUBLIC_DELAY_SEC = 900
    PUBLIC_WINDOW_SEC = 3600
    INVISIBLE_TTL_SEC = 86400
    EMPTY_CORPSE_TTL_SEC = 300

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


# Per-tier roll weights used by tooling/analytics — not exposed via game_config Redis namespace,
# since they are constants that drive offline math rather than runtime tunables.
TIER_WEIGHTS: dict[str, int] = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "epic": 4,
    "legendary": 1,
}
