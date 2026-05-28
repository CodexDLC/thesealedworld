from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.arq import SYSTEM_ARQ_QUEUE, ArqService
from src.backend.infrastructure.exploration.managers import ExplorationKnowledgeRuntimeManager
from src.backend.infrastructure.inventory.managers import InventorySessionManager
from src.backend.infrastructure.rift.managers import RiftPortalStore, RiftRunSessionStore
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def system_dirty_sweeper_task(ctx: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = int(payload.get("limit") or 100)
    redis_managers = ctx["redis_managers"]

    arq = ctx.get("system_arq")
    owns_arq = False
    if arq is None:
        arq = ArqService(queue_name=SYSTEM_ARQ_QUEUE)
        owns_arq = True

    try:
        inventory_char_ids = await _enqueue_inventory(redis_managers.redis, arq, limit=limit)
        knowledge_char_ids = await _enqueue_exploration_knowledge(redis_managers.redis, arq, limit=limit)
        rift_run_ids = await _enqueue_rift_runs(redis_managers.redis, arq, limit=limit)
        archived_rift_portals = await _archive_rift_portals(redis_managers.redis, limit=limit)
    finally:
        if owns_arq:
            await arq.close()

    result = {
        "status": "ok",
        "inventory_enqueued": len(inventory_char_ids),
        "inventory_char_ids": inventory_char_ids,
        "exploration_knowledge_enqueued": len(knowledge_char_ids),
        "exploration_knowledge_char_ids": knowledge_char_ids,
        "rift_run_enqueued": len(rift_run_ids),
        "rift_run_ids": rift_run_ids,
        "rift_portals_archived": len(archived_rift_portals),
        "rift_portal_ids": archived_rift_portals,
    }
    logger.bind(
        inventory_enqueued=result["inventory_enqueued"],
        exploration_knowledge_enqueued=result["exploration_knowledge_enqueued"],
        rift_run_enqueued=result["rift_run_enqueued"],
        rift_portals_archived=result["rift_portals_archived"],
    ).info("SystemDirtySweeperCompleted")
    return result


async def _enqueue_inventory(redis: Any, arq: Any, *, limit: int) -> list[int]:
    inventory_sessions = InventorySessionManager(redis)
    char_ids = await inventory_sessions.scan_dirty(limit=limit)
    for char_id in char_ids:
        await arq.enqueue_job(
            "flush_inventory_session_task",
            {"char_id": char_id, "source": "system_dirty_sweeper"},
        )
    return char_ids


async def _archive_rift_portals(redis: Any, *, limit: int) -> list[str]:
    portals = await RiftPortalStore(redis).archive_due(limit=limit)
    return [str(portal.get("portal_id")) for portal in portals if portal.get("portal_id")]


async def _enqueue_rift_runs(redis: Any, arq: Any, *, limit: int) -> list[str]:
    rift_sessions = RiftRunSessionStore(redis)
    rift_session_ids = await rift_sessions.scan_dirty(limit=limit)
    for rift_session_id in rift_session_ids:
        await arq.enqueue_job(
            "flush_rift_run_task",
            {"rift_session_id": rift_session_id, "source": "system_dirty_sweeper"},
        )
    return rift_session_ids


async def _enqueue_exploration_knowledge(redis: Any, arq: Any, *, limit: int) -> list[int]:
    knowledge = ExplorationKnowledgeRuntimeManager(redis)
    char_ids = await knowledge.scan_dirty_char_ids(limit=limit)
    for char_id in char_ids:
        await arq.enqueue_job(
            "flush_exploration_knowledge_task",
            {"char_id": char_id, "source": "system_dirty_sweeper"},
        )
    return char_ids
