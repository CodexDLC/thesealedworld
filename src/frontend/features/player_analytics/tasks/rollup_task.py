from __future__ import annotations

import asyncio
import time
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from loguru import logger

from src.frontend.core.database.session import get_session_context
from src.frontend.features.player_analytics.repositories.daily_activity_repository import (
    PlayerDailyActivityRepository,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

_ROLLUP_INTERVAL = 600  # 10 minutes
_PRESENCE_MAX_AGE = 86400  # 24 hours — evict entries older than this


async def player_presence_rollup_loop(app: FastAPI) -> None:
    """Background task: persists in-memory player presence to DB every 10 minutes."""
    while True:
        try:
            await asyncio.sleep(_ROLLUP_INTERVAL)
            await _rollup_and_cleanup(app)
        except asyncio.CancelledError:
            # Final flush before exit
            try:
                await _rollup_and_cleanup(app)
            except Exception:
                logger.exception("PlayerPresenceFinalFlushFailed")
            break
        except Exception:
            logger.exception("PlayerPresenceRollupLoopFailed")


async def _rollup_and_cleanup(app: FastAPI) -> None:
    presence: dict[str, float] = getattr(app.state, "player_presence", {})
    if not presence:
        return

    now = time.time()
    cutoff = now - _PRESENCE_MAX_AGE
    today = date.today()
    now_dt = datetime.now(UTC)

    # Clean up stale entries while capturing today's active players
    active_ids: list[str] = []
    stale_ids: list[str] = []
    for pid, ts in list(presence.items()):
        if ts > cutoff:
            active_ids.append(pid)
        else:
            stale_ids.append(pid)

    for pid in stale_ids:
        presence.pop(pid, None)

    if not active_ids:
        return

    async with get_session_context() as session:
        repo = PlayerDailyActivityRepository(session)
        for player_id in active_ids:
            await repo.upsert_activity(player_id, today, now_dt)

    logger.bind(persisted_count=len(active_ids), evicted_count=len(stale_ids)).debug("PlayerPresenceRollupPersisted")
