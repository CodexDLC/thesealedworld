from dataclasses import dataclass

from codex_platform.redis_service import RedisService

from src.backend.core.redis.actor_snapshot_manager import ActorSnapshotManager
from src.backend.core.redis.character_session_manager import CharacterSessionManager


@dataclass
class RedisManagers:
    redis: RedisService
    character_sessions: CharacterSessionManager
    actor_snapshots: ActorSnapshotManager
