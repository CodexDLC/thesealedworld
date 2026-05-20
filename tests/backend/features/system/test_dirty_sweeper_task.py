from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.backend.features.exploration.services.knowledge_runtime import ExplorationKnowledgeRuntimeManager
from src.backend.features.inventory.services.session_manager import InventorySessionManager
from src.backend.features.system.workers.tasks.dirty_sweeper import system_dirty_sweeper_task
from src.shared.schemas.inventory import InventoryRuntimeSessionDTO


@pytest.mark.asyncio
async def test_system_dirty_sweeper_enqueues_domain_flush_jobs(fake_redis_service):
    inventory = InventorySessionManager(fake_redis_service)
    await inventory.set(InventoryRuntimeSessionDTO(char_id=1, is_dirty=True, dirty={"dirty": True}))

    knowledge = ExplorationKnowledgeRuntimeManager(fake_redis_service)
    await knowledge.set(
        2,
        "52_48",
        {
            "movement_xp_spent": 1.0,
            "scouting_xp_spent": 0.0,
            "hunting_xp_spent": 0.0,
            "movement_xp_cap": 1.0,
            "scouting_xp_cap": 1.0,
            "hunting_xp_cap": 1.0,
        },
    )
    arq = AsyncMock()

    result = await system_dirty_sweeper_task(
        {"redis_managers": type("Managers", (), {"redis": fake_redis_service})(), "system_arq": arq},
        {"limit": 10},
    )

    assert result["inventory_char_ids"] == [1]
    assert result["exploration_knowledge_char_ids"] == [2]
    arq.enqueue_job.assert_any_await(
        "flush_inventory_session_task",
        {"char_id": 1, "source": "system_dirty_sweeper"},
    )
    arq.enqueue_job.assert_any_await(
        "flush_exploration_knowledge_task",
        {"char_id": 2, "source": "system_dirty_sweeper"},
    )
