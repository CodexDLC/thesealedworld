from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class CombatConfig(BaseGameConfig):
    namespace = "combat"

    # Parry / Block
    PARRY_SKILL_MULT_PER_POINT: float = 4.0
    SHIELD_BLOCK_SKILL_BONUS_AT_FULL: float = 0.32

    # Accuracy
    BASE_ACCURACY_CHANCE: float = 0.70
    SKILL_ACCURACY_BONUS_AT_FULL: float = 0.30
    ACCURACY_CHANCE_CAP: float = 0.90
    ACCURACY_PENALTY_WEAPON_SKILL_REDUCTION_AT_FULL: float = 0.45
    ACCURACY_PENALTY_STYLE_SKILL_REDUCTION_AT_FULL: float = 0.45
    ACCURACY_PENALTY_MIN_MULTIPLIER: float = 0.10

    # Tokens
    TOKEN_BONUS_CHANCE: float = 0.30

    # Unarmed combat
    UNARMED_MIN_EFFICIENCY: float = 0.5
    UNARMED_MAX_EFFICIENCY: float = 3.0
    UNARMED_NOVICE_SPREAD: float = 0.5
    UNARMED_MASTER_SPREAD: float = 0.1

    # Chaos system
    CHAOS_FIRST_CHECK_DELAY_SECONDS: int = 300
    SESSION_TTL_SECONDS: int = 3600

    # Timeouts
    MIN_TIMEOUT: float = 20.0
    MOVE_RESPONSE_SETTLE_DELAY_SECONDS: float = 0.6

    # UI Accuracy
    STAT_SHEET_BASE_HIT_CHANCE: float = 0.70

    config_metadata = {
        "PARRY_SKILL_MULT_PER_POINT": ConfigEntryMeta(
            label="Множитель навыка парирования",
            description="Сколько навык parrying добавляет к шансу парирования. Больше значение делает обученных бойцов заметно сильнее в защите.",
            group="Парирование и щит",
            unit="multiplier",
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "defense"),
        ),
        "SHIELD_BLOCK_SKILL_BONUS_AT_FULL": ConfigEntryMeta(
            label="Бонус блока щитом от навыка",
            description="Дополнительный шанс shield block при полном skill_shield_mastery.",
            group="Парирование и щит",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "shield"),
        ),
        "BASE_ACCURACY_CHANCE": ConfigEntryMeta(
            label="Базовый шанс попадания",
            description="Стартовая вероятность попадания до бонусов навыка, штрафов оружия/стиля и cap.",
            group="Точность",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="high",
            live_scope="new_exchange",
            tags=("combat", "balance", "accuracy"),
        ),
        "SKILL_ACCURACY_BONUS_AT_FULL": ConfigEntryMeta(
            label="Бонус точности от полного навыка",
            description="Сколько точности добавляет профильный навык оружия или магии при значении навыка 1.0.",
            group="Точность",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "accuracy"),
        ),
        "ACCURACY_CHANCE_CAP": ConfigEntryMeta(
            label="Потолок шанса попадания",
            description="Максимальная итоговая вероятность попадания после всех бонусов и штрафов.",
            group="Точность",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="high",
            live_scope="new_exchange",
            tags=("combat", "balance", "accuracy"),
        ),
        "ACCURACY_PENALTY_WEAPON_SKILL_REDUCTION_AT_FULL": ConfigEntryMeta(
            label="Снижение штрафа точности оружием",
            description="Как сильно профильное владение оружием снижает штраф точности при полном навыке.",
            group="Точность",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "accuracy"),
        ),
        "ACCURACY_PENALTY_STYLE_SKILL_REDUCTION_AT_FULL": ConfigEntryMeta(
            label="Снижение штрафа точности стилем",
            description="Как сильно тактический стиль снижает штраф точности при полном навыке.",
            group="Точность",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "accuracy"),
        ),
        "ACCURACY_PENALTY_MIN_MULTIPLIER": ConfigEntryMeta(
            label="Минимальный множитель штрафа точности",
            description="Нижняя граница штрафного множителя. Не дает навыкам полностью убрать penalty branch.",
            group="Точность",
            unit="multiplier",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "accuracy"),
        ),
        "TOKEN_BONUS_CHANCE": ConfigEntryMeta(
            label="Шанс бонусного токена",
            description="Вероятность получить дополнительный боевой token при token roll.",
            group="Ресурсы боя",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "tokens"),
        ),
        "UNARMED_MIN_EFFICIENCY": ConfigEntryMeta(
            label="Минимальная эффективность безоружки",
            description="Множитель силы для unarmed атаки при нулевом skill_unarmed.",
            group="Безоружный бой",
            unit="multiplier",
            min_value=0.0,
            max_value=5.0,
            step=0.1,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "unarmed"),
        ),
        "UNARMED_MAX_EFFICIENCY": ConfigEntryMeta(
            label="Максимальная эффективность безоружки",
            description="Множитель силы для unarmed атаки при полном skill_unarmed.",
            group="Безоружный бой",
            unit="multiplier",
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "balance", "unarmed"),
        ),
        "UNARMED_NOVICE_SPREAD": ConfigEntryMeta(
            label="Разброс безоружки новичка",
            description="Damage spread для unarmed атаки при нулевом навыке.",
            group="Безоружный бой",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="low",
            live_scope="new_exchange",
            tags=("combat", "balance", "unarmed"),
        ),
        "UNARMED_MASTER_SPREAD": ConfigEntryMeta(
            label="Разброс безоружки мастера",
            description="Минимальный damage spread для unarmed атаки при высоком навыке.",
            group="Безоружный бой",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="low",
            live_scope="new_exchange",
            tags=("combat", "balance", "unarmed"),
        ),
        "CHAOS_FIRST_CHECK_DELAY_SECONDS": ConfigEntryMeta(
            label="Задержка первой проверки хаоса",
            description="Сколько секунд после старта боя ждать до первого chaos check.",
            group="Сессии и фоновые проверки",
            unit="seconds",
            min_value=0.0,
            max_value=3600.0,
            step=10.0,
            risk="medium",
            live_scope="next_check",
            tags=("combat", "runtime", "chaos"),
        ),
        "SESSION_TTL_SECONDS": ConfigEntryMeta(
            label="Время жизни боевой сессии",
            description="TTL Redis-состояния боя. 3600 = один час.",
            group="Сессии и фоновые проверки",
            unit="seconds",
            min_value=60.0,
            max_value=86400.0,
            step=60.0,
            risk="high",
            live_scope="new_session",
            tags=("combat", "runtime", "ttl"),
        ),
        "MIN_TIMEOUT": ConfigEntryMeta(
            label="Минимальный таймаут хода",
            description="Базовый таймаут для хода (в секундах), если игрок не AFK.",
            group="Сессии и фоновые проверки",
            unit="seconds",
            min_value=5.0,
            max_value=120.0,
            step=1.0,
            risk="medium",
            live_scope="new_exchange",
            tags=("combat", "runtime", "timeout"),
        ),
        "MOVE_RESPONSE_SETTLE_DELAY_SECONDS": ConfigEntryMeta(
            label="Задержка обработки хода",
            description="Искусственная задержка (в секундах) перед отдачей результата, чтобы дать движку время на обработку.",
            group="Сессии и фоновые проверки",
            unit="seconds",
            min_value=0.0,
            max_value=5.0,
            step=0.1,
            risk="low",
            live_scope="new_exchange",
            tags=("combat", "runtime", "delay"),
        ),
        "STAT_SHEET_BASE_HIT_CHANCE": ConfigEntryMeta(
            label="UI Базовый шанс попадания",
            description="Базовый шанс попадания для отображения в статистике персонажа.",
            group="Точность",
            unit="ratio",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            risk="low",
            live_scope="immediate",
            tags=("combat", "ui", "accuracy"),
        ),
    }
