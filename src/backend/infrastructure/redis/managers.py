from dataclasses import dataclass

from codex_platform.redis_service import RedisService

from src.backend.infrastructure.redis.actor_snapshot_manager import ActorSnapshotManager
from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager
from src.backend.infrastructure.redis.scenario.session_manager import ScenarioSessionManager
from src.backend.infrastructure.redis.world import WorldLocationStore


@dataclass
class RedisManagers:
    redis: RedisService
    character_sessions: CharacterSessionManager
    actor_snapshots: ActorSnapshotManager
    scenario_sessions: ScenarioSessionManager
    world_locations: WorldLocationStore
