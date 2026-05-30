from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from codex_platform.redis_service import RedisService

from src.backend.infrastructure.actor_commitments import ActorCommitmentManager
from src.backend.infrastructure.actor_state.managers import CharacterSessionManager
from src.backend.infrastructure.expedition.managers import ExpeditionRedisManager
from src.backend.infrastructure.game_lobby.managers import StartingImprintDistributionManager
from src.backend.infrastructure.inventory.managers import InventorySessionManager
from src.backend.infrastructure.rift.managers import RiftPortalStore
from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager
from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
from src.backend.infrastructure.world import WorldLocationStore

if TYPE_CHECKING:
    from src.backend.infrastructure.game_config.manager import GameConfigManager


@dataclass
class RedisManagers:
    redis: RedisService
    character_sessions: CharacterSessionManager
    actor_commitments: ActorCommitmentManager
    scenario_sessions: ScenarioSessionManager
    scenario_content: ScenarioContentManager
    world_locations: WorldLocationStore
    expeditions: ExpeditionRedisManager
    inventory_sessions: InventorySessionManager
    rift_portals: RiftPortalStore
    starting_imprints: StartingImprintDistributionManager


def build_redis_managers(
    redis: RedisService,
    game_config: GameConfigManager | None = None,
) -> RedisManagers:
    return RedisManagers(
        redis=redis,
        character_sessions=CharacterSessionManager(redis),
        actor_commitments=ActorCommitmentManager(redis),
        scenario_sessions=ScenarioSessionManager(redis, game_config),
        scenario_content=ScenarioContentManager(redis),
        world_locations=WorldLocationStore(redis),
        expeditions=ExpeditionRedisManager(redis),
        inventory_sessions=InventorySessionManager(redis),
        rift_portals=RiftPortalStore(redis),
        starting_imprints=StartingImprintDistributionManager(redis),
    )
