from dataclasses import dataclass

from codex_platform.redis_service import RedisService

from src.backend.features.character.managers import CharacterSessionManager
from src.backend.features.expedition.redis_manager import ExpeditionRedisManager
from src.backend.infrastructure.actor_commitments import ActorCommitmentManager
from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager
from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
from src.backend.infrastructure.world import WorldLocationStore


@dataclass
class RedisManagers:
    redis: RedisService
    character_sessions: CharacterSessionManager
    actor_commitments: ActorCommitmentManager
    scenario_sessions: ScenarioSessionManager
    scenario_content: ScenarioContentManager
    world_locations: WorldLocationStore
    expeditions: ExpeditionRedisManager


def build_redis_managers(redis: RedisService) -> RedisManagers:
    return RedisManagers(
        redis=redis,
        character_sessions=CharacterSessionManager(redis),
        actor_commitments=ActorCommitmentManager(redis),
        scenario_sessions=ScenarioSessionManager(redis),
        scenario_content=ScenarioContentManager(redis),
        world_locations=WorldLocationStore(redis),
        expeditions=ExpeditionRedisManager(redis),
    )
