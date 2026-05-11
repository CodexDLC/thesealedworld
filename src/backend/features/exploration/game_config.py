from src.backend.infrastructure.game_config.base import BaseGameConfig


class ExplorationConfig(BaseGameConfig):
    namespace = "exploration"

    TRAVEL_TIME_MULT: float = 1.0
    ENCOUNTER_BASE_CHANCE: float = 0.15
    ENCOUNTER_WEIGHT_BASE: float = 1.0
    EVENT_CHANCE_PER_STEP: float = 0.08
