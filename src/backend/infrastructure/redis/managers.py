from dataclasses import dataclass

from codex_platform.redis_service import RedisService

from src.backend.infrastructure.actor_state import ActorSnapshotManager, CharacterSessionManager
from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
from src.backend.infrastructure.world import WorldLocationStore


@dataclass
class RedisManagers:
    redis: RedisService
    character_sessions: CharacterSessionManager
    actor_snapshots: ActorSnapshotManager
    scenario_sessions: ScenarioSessionManager
    world_locations: WorldLocationStore
