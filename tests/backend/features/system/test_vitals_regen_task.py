from unittest.mock import AsyncMock

import pytest

from src.backend.features.system.workers.tasks.vitals_regen import online_vitals_regen_task
from src.backend.infrastructure.actor_state.managers import CharacterSessionManager


@pytest.mark.asyncio
async def test_online_vitals_regen_task_updates_only_incomplete_vitals_and_requests_refresh(
    fake_redis_service,
    fake_redis_client,
) -> None:
    fake_redis_client.store["game:ac:7"] = {
        "char_id": 7,
        "state": "exploration",
        "attributes": {"strength": 15, "endurance": 16, "mental": 13},
        "items": {},
        "vitals": {
            "hp": {"cur": 20, "max": 70, "regen": 2.0},
            "energy": {"cur": 31, "max": 31, "regen": 1.0},
            "stamina": {"cur": 16, "max": 16, "regen": 1.0},
            "last_update": 100.0,
        },
    }
    fake_redis_client.store["game:ac:8"] = {
        "char_id": 8,
        "state": "exploration",
        "attributes": {"strength": 15, "endurance": 16, "mental": 13},
        "items": {},
        "vitals": {
            "hp": {"cur": 70, "max": 70, "regen": 2.0},
            "energy": {"cur": 31, "max": 31, "regen": 1.0},
            "stamina": {"cur": 16, "max": 16, "regen": 1.0},
            "last_update": 100.0,
        },
    }
    events = AsyncMock()
    managers = type(
        "Managers",
        (),
        {
            "redis": fake_redis_service,
            "character_sessions": CharacterSessionManager(fake_redis_service),
        },
    )()

    result = await online_vitals_regen_task(
        {"redis_managers": managers, "events": events},
        {"limit": 10, "now": 130.0},
    )

    assert result["processed_char_ids"] == [7]
    assert result["refreshed_char_ids"] == [7]
    assert fake_redis_client.store["game:ac:7"]["vitals"]["hp"]["cur"] == 50
    assert fake_redis_client.store["game:ac:8"]["vitals"]["hp"]["cur"] == 70
    events.publish.assert_awaited()


@pytest.mark.asyncio
async def test_online_vitals_regen_task_skips_combat_sessions(
    fake_redis_service,
    fake_redis_client,
) -> None:
    fake_redis_client.store["game:ac:7"] = {
        "char_id": 7,
        "state": "combats",
        "attributes": {"strength": 15, "endurance": 16, "mental": 13},
        "items": {},
        "vitals": {
            "hp": {"cur": 20, "max": 70, "regen": 2.0},
            "energy": {"cur": 31, "max": 31, "regen": 1.0},
            "stamina": {"cur": 16, "max": 16, "regen": 1.0},
            "last_update": 100.0,
        },
    }
    events = AsyncMock()
    managers = type(
        "Managers",
        (),
        {
            "redis": fake_redis_service,
            "character_sessions": CharacterSessionManager(fake_redis_service),
        },
    )()

    result = await online_vitals_regen_task(
        {"redis_managers": managers, "events": events},
        {"limit": 10, "now": 130.0},
    )

    assert result["processed_char_ids"] == []
    assert result["refreshed_char_ids"] == []
    assert fake_redis_client.store["game:ac:7"]["vitals"]["hp"]["cur"] == 20
    events.publish.assert_not_awaited()
