from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.database.session import get_session_context
from src.backend.core.mongo import get_mongo_provider
from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.features.rift.integrations.runtime import RiftRuntimeNotFoundError
from src.backend.infrastructure.rift.managers import (
    RiftInstanceStore,
    RiftPortalStore,
    RiftPresenceStore,
    RiftRestoreLock,
    RiftRunSessionStore,
)
from src.backend.infrastructure.rift.repositories import RiftMembershipRepository
from src.backend.infrastructure.rift.repositories.snapshots import RiftRuntimeSnapshotRepository
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def flush_rift_run_task(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    rift_session_id = str(payload["rift_session_id"])
    redis = ctx["redis_managers"].redis

    async with get_session_context() as db:
        integration = RiftRuntimeIntegration(
            instance_store=RiftInstanceStore(redis),
            session_store=RiftRunSessionStore(redis),
            presence_store=RiftPresenceStore(redis),
            portal_store=RiftPortalStore(redis),
            membership_repository=RiftMembershipRepository(db),
            snapshot_repository=RiftRuntimeSnapshotRepository(get_mongo_provider().database()),
            restore_lock=RiftRestoreLock(redis),
        )
        try:
            result = await integration.flush_dirty_run_session(rift_session_id)
        except RiftRuntimeNotFoundError:
            logger.bind(rift_session_id=rift_session_id).warning("RiftDirtyFlushSkippedMissingRuntime")
            return {"status": "skipped", "reason": "missing_runtime", "rift_session_id": rift_session_id}

    logger.bind(rift_session_id=rift_session_id, status=result.get("status")).info("RiftDirtyFlushCompleted")
    return result
