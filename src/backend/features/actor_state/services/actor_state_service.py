from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Any

from src.backend.core.database import get_session_context
from src.backend.features.actor_state.dto.snapshot import ActorSnapshotBatchResult
from src.backend.features.actor_state.runtime.assemblers import monster_assembler, player_assembler
from src.backend.features.actor_state.runtime.sections import resolve_sections
from src.backend.infrastructure.redis.actor_snapshot_manager import ActorSnapshotManager

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

SessionContextFactory = Callable[[], AbstractAsyncContextManager[Any]]


class ActorStateService:
    def __init__(
        self,
        snapshot_manager: ActorSnapshotManager,
        redis: RedisService,
        session_factory: SessionContextFactory = get_session_context,
    ) -> None:
        self.snapshot_manager = snapshot_manager
        self.redis = redis
        self.session_factory = session_factory

    async def prepare_snapshots(
        self,
        session_id: str,
        player_ids: list[int],
        monster_ids: list[str],
        ttl: int = ActorSnapshotManager.DEFAULT_TTL_SECONDS,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
    ) -> ActorSnapshotBatchResult:
        sections = resolve_sections(include, exclude or set())

        async with self.session_factory() as session:
            player_snapshots, monster_snapshots = await asyncio.gather(
                player_assembler.build_snapshots(session, self.redis, player_ids, sections),
                monster_assembler.build_snapshots(session, monster_ids, sections),
            )

        snapshots = {
            **{f"{session_id}:player:{char_id}": snapshot for char_id, snapshot in player_snapshots.items()},
            **{f"{session_id}:monster:{monster_id}": snapshot for monster_id, snapshot in monster_snapshots.items()},
        }
        saved = await self.snapshot_manager.save_snapshots(snapshots, ttl=ttl)

        failed_players = [char_id for char_id in player_ids if f"{session_id}:player:{char_id}" not in saved]
        failed_monsters = [
            monster_id for monster_id in monster_ids if f"{session_id}:monster:{monster_id}" not in saved
        ]

        return ActorSnapshotBatchResult(
            snapshot_keys=saved,
            failed_players=failed_players,
            failed_monsters=failed_monsters,
            counts={
                "players": len(player_ids) - len(failed_players),
                "monsters": len(monster_ids) - len(failed_monsters),
                "snapshots": len(saved),
            },
        )
