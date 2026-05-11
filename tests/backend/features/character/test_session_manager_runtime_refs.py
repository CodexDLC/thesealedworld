import pytest

from src.backend.features.character.managers.session import CharacterSessionManager


@pytest.mark.asyncio
async def test_inventory_runtime_refs_and_projection_do_not_mark_character_dirty(
    fake_redis_service,
    fake_redis_client,
) -> None:
    fake_redis_client.store["game:ac:7"] = {"char_id": 7, "sessions": {}, "items": {}}
    manager = CharacterSessionManager(fake_redis_service)

    await manager.set_inventory_session(7, "game:inventory:7")
    await manager.set_items_projection(7, {"layout": {"equipment": {}}, "by_id": {}})
    await manager.clear_inventory_session(7)

    active_character = fake_redis_client.store["game:ac:7"]
    assert active_character["sessions"]["inventory_id"] is None
    assert active_character["items"] == {"layout": {"equipment": {}}, "by_id": {}}
    assert "sync_dirty" not in active_character


@pytest.mark.asyncio
async def test_arena_runtime_ref_marks_character_dirty(
    fake_redis_service,
    fake_redis_client,
) -> None:
    fake_redis_client.store["game:ac:7"] = {"char_id": 7, "sessions": {}, "items": {}}
    manager = CharacterSessionManager(fake_redis_service)

    await manager.set_arena_session(7, "arena:runtime:1")

    active_character = fake_redis_client.store["game:ac:7"]
    assert active_character["sessions"]["arena_id"] == "arena:runtime:1"
    assert active_character["sync_dirty"]["dirty"] is True
    assert "$.sessions.arena_id" in active_character["sync_dirty"]["paths"]


@pytest.mark.asyncio
async def test_encounter_runtime_ref_marks_character_dirty(
    fake_redis_service,
    fake_redis_client,
) -> None:
    fake_redis_client.store["game:ac:7"] = {"char_id": 7, "sessions": {}, "items": {}}
    manager = CharacterSessionManager(fake_redis_service)

    await manager.set_encounter_session(7, "encounter-1")
    await manager.clear_encounter_session(7)

    active_character = fake_redis_client.store["game:ac:7"]
    assert active_character["sessions"]["encounter_id"] is None
    assert active_character["sync_dirty"]["dirty"] is True
    assert "$.sessions.encounter_id" in active_character["sync_dirty"]["paths"]


@pytest.mark.asyncio
async def test_reset_main_runtime_refs_to_exploration_clears_blocking_refs(
    fake_redis_service,
    fake_redis_client,
) -> None:
    fake_redis_client.store["game:ac:7"] = {
        "char_id": 7,
        "state": "combats",
        "prev_state": "scenario",
        "sessions": {
            "scenario_id": "scenario-1",
            "combat_id": "combat-1",
            "combat_finalization_id": "combat-final-1",
            "encounter_id": "encounter-1",
            "arena_id": "arena-1",
            "inventory_id": "inventory-1",
        },
        "active_quest": "awakening_rift",
    }
    manager = CharacterSessionManager(fake_redis_service)

    await manager.reset_main_runtime_refs_to_exploration(7)

    active_character = fake_redis_client.store["game:ac:7"]
    assert active_character["state"] == "exploration"
    assert active_character["prev_state"] == "exploration"
    assert active_character["sessions"]["scenario_id"] is None
    assert active_character["sessions"]["combat_id"] is None
    assert active_character["sessions"]["combat_finalization_id"] is None
    assert active_character["sessions"]["encounter_id"] is None
    assert active_character["sessions"]["arena_id"] is None
    assert active_character["sessions"]["inventory_id"] == "inventory-1"
    assert active_character["active_quest"] is None
