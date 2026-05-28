from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.backend.features.system.workers.tasks.dirty_sweeper import system_dirty_sweeper_task
from src.backend.infrastructure.exploration.managers import ExplorationKnowledgeRuntimeManager
from src.backend.infrastructure.inventory.managers import InventorySessionManager
from src.backend.infrastructure.rift.managers import RiftPortalStore, RiftRunSessionStore
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
    portals = RiftPortalStore(fake_redis_service)
    await portals.save_portal(
        {
            "portal_id": "portal-1",
            "rift_session_id": "rift:run:1",
            "status": "completed",
        }
    )
    rift_sessions = RiftRunSessionStore(fake_redis_service)
    await rift_sessions.create_session({"rift_session_id": "rift:run:dirty", "rift_instance_id": "rift-1"})
    await rift_sessions.mark_dirty("rift:run:dirty", reason="travel_completed", paths=["$.current_node_id"])
    arq = AsyncMock()

    result = await system_dirty_sweeper_task(
        {"redis_managers": type("Managers", (), {"redis": fake_redis_service})(), "system_arq": arq},
        {"limit": 10},
    )

    assert result["inventory_char_ids"] == [1]
    assert result["exploration_knowledge_char_ids"] == [2]
    assert result["rift_run_ids"] == ["rift:run:dirty"]
    assert result["rift_portal_ids"] == ["portal-1"]
    arq.enqueue_job.assert_any_await(
        "flush_inventory_session_task",
        {"char_id": 1, "source": "system_dirty_sweeper"},
    )
    arq.enqueue_job.assert_any_await(
        "flush_exploration_knowledge_task",
        {"char_id": 2, "source": "system_dirty_sweeper"},
    )
    arq.enqueue_job.assert_any_await(
        "flush_rift_run_task",
        {"rift_session_id": "rift:run:dirty", "source": "system_dirty_sweeper"},
    )
