"""Cabinet-exposed AI/training settings for combat.

Kept separate from ``CombatConfig`` (combat math) so admins can clearly
distinguish balance knobs from AI training/policy knobs in the cabinet UI.
"""

from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


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

    # Minutes before an AI simulation report is considered stale.
    STALE_RUNNING_REPORT_MINUTES: int = 20

    # Max number of items returned in analytics drilldown.
    ANALYTICS_DRILLDOWN_LIMIT: int = 500

    # Chaos task timeouts
    CHAOS_MAX_INACTIVITY_SEC: int = 600
    CHAOS_NEXT_CHECK_DELAY_SEC: int = 300

    config_metadata = {
        "ACTIVE_POLICY_ID": ConfigEntryMeta(
            label="Активная политика ИИ",
            description="Версия обучения для новых боев. Пусто означает runtime default или env override.",
            group="Live policy",
            unit="policy_id",
            risk="high",
            live_scope="new_session",
            tags=("combat_ai", "policy"),
        ),
        "EXPLORATION_RANDOMNESS_MULT": ConfigEntryMeta(
            label="Множитель случайности",
            description="Управляет случайностью выбора хода: 0.0 почти детерминированно, 1.0 как в policy.",
            group="Live policy",
            unit="multiplier",
            min_value=0.0,
            max_value=3.0,
            step=0.05,
            risk="medium",
            live_scope="new_ai_decision",
            tags=("combat_ai", "policy"),
        ),
        "TRAINING_ENABLED": ConfigEntryMeta(
            label="Разрешить обучение",
            description="Флаг для training entry points. В live-бой сам по себе обученные веса не включает.",
            group="Training",
            risk="high",
            live_scope="new_training_request",
            tags=("combat_ai", "training", "ops"),
        ),
        "TRAINING_SEED": ConfigEntryMeta(
            label="Seed обучения",
            description="Фиксирует воспроизводимость тренировок. 0 оставляет текущий дефолт.",
            group="Training",
            min_value=0.0,
            max_value=2147483647.0,
            step=1.0,
            risk="low",
            live_scope="new_training_request",
            tags=("combat_ai", "training"),
        ),
        "STALE_RUNNING_REPORT_MINUTES": ConfigEntryMeta(
            label="Stale Running Report Timeout",
            description="Minutes before an AI simulation report is considered stale.",
            group="AI Simulation",
            unit="minutes",
            min_value=1.0,
            max_value=1440.0,
            step=1.0,
            risk="low",
            tags=("combat_ai", "simulation", "timeout"),
        ),
        "ANALYTICS_DRILLDOWN_LIMIT": ConfigEntryMeta(
            label="Analytics Drilldown Limit",
            description="Max number of items returned in analytics drilldown.",
            group="Analytics",
            unit="count",
            min_value=1.0,
            max_value=10000.0,
            step=10.0,
            risk="low",
            tags=("combat_ai", "analytics", "limits"),
        ),
        "CHAOS_MAX_INACTIVITY_SEC": ConfigEntryMeta(
            label="Максимальное время бездействия",
            description="Время (в секундах), после которого сессия считается зависшей и спавнится чистильщик хаоса.",
            group="Chaos Watchdog",
            unit="seconds",
            min_value=60.0,
            max_value=3600.0,
            step=60.0,
            risk="medium",
            live_scope="next_check",
            tags=("combat_ai", "runtime", "chaos"),
        ),
        "CHAOS_NEXT_CHECK_DELAY_SEC": ConfigEntryMeta(
            label="Задержка между проверками",
            description="Интервал (в секундах) между запусками watchdog'а хаоса для одной сессии.",
            group="Chaos Watchdog",
            unit="seconds",
            min_value=60.0,
            max_value=1800.0,
            step=60.0,
            risk="low",
            live_scope="next_check",
            tags=("combat_ai", "runtime", "chaos"),
        ),
    }
