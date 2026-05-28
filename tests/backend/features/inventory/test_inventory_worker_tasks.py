from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.backend.features.inventory.workers.tasks.session_tasks import inventory_dirty_sweeper_task
from src.backend.infrastructure.inventory.managers import InventorySessionManager
from src.shared.schemas.inventory import InventoryRuntimeItemDTO, InventoryRuntimeSessionDTO


@pytest.mark.asyncio
async def test_inventory_dirty_sweeper_enqueues_flush_for_dirty_sessions(fake_redis_service):
    sessions = InventorySessionManager(fake_redis_service)
    clean = InventoryRuntimeSessionDTO(char_id=1)
    dirty = InventoryRuntimeSessionDTO(
        char_id=2,
        by_id={
            "item-1": InventoryRuntimeItemDTO(
                item_id="item-1",
                base_id="item",
                item_type="weapon",
                name="item-1",
            )
        },
        is_dirty=True,
        dirty={"dirty": True},
    )
    await sessions.set(clean)
    await sessions.set(dirty)
    arq = AsyncMock()

    result = await inventory_dirty_sweeper_task(
        {"redis_managers": type("Managers", (), {"redis": fake_redis_service})(), "system_arq": arq},
        {"limit": 10},
    )

    assert result == {"status": "ok", "enqueued": 1, "char_ids": [2]}
    arq.enqueue_job.assert_awaited_once_with(
        "flush_inventory_session_task",
        {"char_id": 2, "source": "inventory_dirty_sweeper"},
    )
