from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class ScenarioConfig(BaseGameConfig):
    namespace = "scenario"

    # Session lifetime in Redis. Phase 4 wires this into ScenarioSessionManager.
    SESSION_TTL_SECONDS: int = 24 * 60 * 60

    BACKUP_INTERVAL: int = 3
    COMBAT_TTL_SECONDS: int = 86400

    config_metadata = {
        "SESSION_TTL_SECONDS": ConfigEntryMeta(
            label="Время жизни сценарной сессии",
            description="TTL Redis-сессии сценария. 86400 = 24 часа.",
            group="Сессии",
            unit="seconds",
            min_value=300.0,
            max_value=604800.0,
            step=300.0,
            risk="medium",
            live_scope="new_session",
            tags=("scenario", "runtime", "ttl"),
        ),
        "BACKUP_INTERVAL": ConfigEntryMeta(
            label="Интервал бекапа",
            description="Количество шагов (узлов), через которое делается полный бекап сессии в БД.",
            group="Сессии",
            unit="count",
            min_value=1.0,
            max_value=20.0,
            step=1.0,
            risk="medium",
            live_scope="immediate",
            tags=("scenario", "runtime", "backup"),
        ),
        "COMBAT_TTL_SECONDS": ConfigEntryMeta(
            label="Время жизни боя в сценарии",
            description="TTL Redis-сессии боя внутри сценария. 86400 = 24 часа.",
            group="Бои",
            unit="seconds",
            min_value=300.0,
            max_value=604800.0,
            step=300.0,
            risk="high",
            live_scope="new_session",
            tags=("scenario", "runtime", "ttl"),
        ),
    }
