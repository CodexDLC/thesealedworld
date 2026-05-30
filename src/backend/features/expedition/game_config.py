from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class ExpeditionConfig(BaseGameConfig):
    namespace = "expedition"

    config_metadata = {
        "PLAYER_CORPSE_TTL_SECONDS": ConfigEntryMeta(
            label="Время жизни трупа игрока",
            description="Время (в секундах), в течение которого труп игрока доступен для лута.",
            group="Смерть",
            unit="seconds",
            min_value=3600.0,
            max_value=604800.0,
            step=3600.0,
            risk="high",
            live_scope="new_exchange",
            tags=("expedition", "corpse", "ttl"),
        ),
    }

    PLAYER_CORPSE_TTL_SECONDS = 86400.0
