from __future__ import annotations

import pytest

from src.backend.features.exploration.services.knowledge_runtime import ExplorationKnowledgeRuntimeManager
from src.backend.features.exploration.services.knowledge_service import ExplorationKnowledgeService


@pytest.mark.asyncio
async def test_location_knowledge_caps_base_exploration_rewards(fake_redis_service):
    runtime = ExplorationKnowledgeRuntimeManager(fake_redis_service)
    service = ExplorationKnowledgeService(
        runtime,
        default_caps={"movement": 3.0, "scouting": 2.0, "hunting": 4.0},
    )

    first = await service.cap_rewards(1, "52_48", {"skill_pathfinder": 0.003})
    second = await service.cap_rewards(1, "52_48", {"skill_pathfinder": 0.004})
    third = await service.cap_rewards(1, "52_48", {"skill_pathfinder": 0.010})
    exhausted = await service.cap_rewards(1, "52_48", {"skill_pathfinder": 0.100})

    assert first == {"skill_pathfinder": 0.003}
    assert second == {"skill_pathfinder": 0.004}
    assert third == {"skill_pathfinder": 0.01}
    assert exhausted == {}
    document = await runtime.get(1, "52_48")
    assert document is not None
    assert document["movement_xp_spent"] == pytest.approx(3.0)
    assert await runtime.dirty_loc_ids(1) == ["52_48"]


@pytest.mark.asyncio
async def test_location_knowledge_reports_fully_studied_after_movement_and_scouting_caps(fake_redis_service):
    runtime = ExplorationKnowledgeRuntimeManager(fake_redis_service)
    service = ExplorationKnowledgeService(
        runtime,
        default_caps={"movement": 1.0, "scouting": 1.0, "hunting": 4.0},
    )

    await service.cap_rewards(1, "52_48", {"skill_pathfinder": 0.010})
    await service.cap_rewards(1, "52_48", {"skill_scouting": 0.020})

    document = await runtime.get(1, "52_48")
    assert document is not None
    assert document["knowledge_status"] == "fully_studied"
