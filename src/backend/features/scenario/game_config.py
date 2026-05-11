from src.backend.infrastructure.game_config.base import BaseGameConfig


class ScenarioConfig(BaseGameConfig):
    namespace = "scenario"

    ENCOUNTER_WEIGHT_BASE: float = 1.0
    ENCOUNTER_WEIGHT_RARE: float = 0.15
    MAX_ACTIVE_SCENARIOS_PER_PLAYER: int = 1
