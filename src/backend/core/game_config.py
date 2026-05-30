from src.backend.infrastructure.game_config.base import BaseGameConfig, ConfigEntryMeta


class CoreConfig(BaseGameConfig):
    namespace = "core"

    SKILL_PROGRESSION_BASE_RATE: float = 0.00005

    config_metadata = {
        "SKILL_PROGRESSION_BASE_RATE": ConfigEntryMeta(
            label="Base Skill Progression Rate",
            description="Global multiplier for skill xp gain.",
            group="Progression",
            unit="multiplier",
            min_value=0.0,
            max_value=1.0,
            step=0.00001,
            risk="high",
            tags=("core", "balance", "progression"),
        ),
    }
