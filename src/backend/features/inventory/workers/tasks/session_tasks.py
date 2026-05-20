from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.arq import SYSTEM_ARQ_QUEUE, ArqService
from src.backend.core.database.session import get_session_context
from src.backend.features.inventory.integrations import InventoryStreamClient
from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.inventory.services.inventory_service import InventoryService
from src.backend.features.inventory.services.session_manager import InventorySessionManager


async def flush_inventory_session_task(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    char_id = int(payload["char_id"])
    redis_managers = ctx["redis_managers"]

    inventory_sessions = InventorySessionManager(redis_managers.redis)
    session = await inventory_sessions.get(char_id)
    if session is None:
        logger.info("InventoryTask | flush skipped missing_session char_id={}", char_id)
        return {"status": "skipped", "reason": "missing_session", "char_id": char_id}
    if not session.is_dirty and session.dirty.get("dirty") is not True:
        logger.info("InventoryTask | flush skipped clean_session char_id={}", char_id)
        return {"status": "skipped", "reason": "clean_session", "char_id": char_id}

    async with get_session_context() as db:
        service = InventoryService(
            repository=InventoryItemRepository(db),
            inventory_sessions=inventory_sessions,
            character_sessions=redis_managers.character_sessions,
            stream_client=InventoryStreamClient(ctx["events"]),
        )
        await service.flush_session(session)

    await inventory_sessions.clear_dirty(char_id)
    logger.info("InventoryTask | flush complete char_id={} item_count={}", char_id, len(session.by_id))
    return {"status": "ok", "char_id": char_id, "item_count": len(session.by_id)}


async def inventory_dirty_sweeper_task(ctx: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    redis_managers = ctx["redis_managers"]
    limit = int(payload.get("limit") or 100)
    inventory_sessions = InventorySessionManager(redis_managers.redis)
    dirty_char_ids = await inventory_sessions.scan_dirty(limit=limit)

    arq = ctx.get("system_arq")
    owns_arq = False
    if arq is None:
        arq = ArqService(queue_name=SYSTEM_ARQ_QUEUE)
        owns_arq = True
    try:
        for char_id in dirty_char_ids:
            await arq.enqueue_job(
                "flush_inventory_session_task",
                {"char_id": char_id, "source": "inventory_dirty_sweeper"},
            )
    finally:
        if owns_arq:
            await arq.close()

    logger.info("InventoryTask | dirty_sweeper enqueued count={}", len(dirty_char_ids))
    return {"status": "ok", "enqueued": len(dirty_char_ids), "char_ids": dirty_char_ids}
