from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.arq import SYSTEM_ARQ_QUEUE, ArqService
from src.backend.features.exploration.services.knowledge_runtime import ExplorationKnowledgeRuntimeManager
from src.backend.features.inventory.services.session_manager import InventorySessionManager


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
    finally:
        if owns_arq:
            await arq.close()

    result = {
        "status": "ok",
        "inventory_enqueued": len(inventory_char_ids),
        "inventory_char_ids": inventory_char_ids,
        "exploration_knowledge_enqueued": len(knowledge_char_ids),
        "exploration_knowledge_char_ids": knowledge_char_ids,
    }
    logger.info("SystemDirtySweeper | result={}", result)
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


async def _enqueue_exploration_knowledge(redis: Any, arq: Any, *, limit: int) -> list[int]:
    knowledge = ExplorationKnowledgeRuntimeManager(redis)
    char_ids = await knowledge.scan_dirty_char_ids(limit=limit)
    for char_id in char_ids:
        await arq.enqueue_job(
            "flush_exploration_knowledge_task",
            {"char_id": char_id, "source": "system_dirty_sweeper"},
        )
    return char_ids
