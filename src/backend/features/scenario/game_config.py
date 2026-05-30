from src.backend.infrastructure.game_config.base import BaseGameConfig


class ScenarioConfig(BaseGameConfig):
    namespace = "scenario"

    # Session lifetime in Redis. Phase 4 wires this into ScenarioSessionManager.
    SESSION_TTL_SECONDS: int = 24 * 60 * 60
