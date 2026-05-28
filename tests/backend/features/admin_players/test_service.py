from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.backend.features.admin_players.services import AdminPlayerReadService


class FakeRepository:
    def __init__(self, *, character: object | None = None) -> None:
        self.user_id = uuid4()
        self.character = character or _character(self.user_id)

    async def count_characters_for_user(self, user_id):
        assert user_id == self.user_id
        return 1

    async def list_characters_for_user(self, user_id, *, limit: int, offset: int):
        assert user_id == self.user_id
        assert limit == 25
        assert offset == 0
        return [self.character]

    async def get_character_detail(self, character_id: int):
        if self.character is None:
            return None
        assert character_id == self.character.character_id
        return self.character

    async def list_active_items(self, character_id: int):
        assert character_id == self.character.character_id
        return [
            (_item("sword-1", slot="main_hand", tier=3), _placement("equipped", slot="main_hand")),
            (_item("potion-1", slot="belt_slot_1", tier=1), _placement("belt", slot="belt_slot_1")),
        ]

    async def count_carried_items(self, character_id: int):
        assert character_id == self.character.character_id
        return 2

    async def list_carried_items(self, character_id: int, *, limit: int, offset: int):
        assert character_id == self.character.character_id
        assert limit == 50
        assert offset == 0
        return [(_item("cloak-1", slot="outer_garment", tier=2), _placement("backpack", position_index=0))]


@pytest.mark.unit
async def test_admin_player_service_lists_user_characters() -> None:
    repo = FakeRepository()
    service = AdminPlayerReadService(repo)

    result = await service.list_characters_for_user(repo.user_id, limit=25, offset=0)

    assert result.user_id == repo.user_id
    assert result.total == 1
    assert result.items[0].character_id == 77
    assert result.items[0].name == "Test Hero"
    assert result.items[0].location_id == "start_village"


@pytest.mark.unit
async def test_admin_player_service_builds_character_detail_slots_and_inventory() -> None:
    repo = FakeRepository()
    service = AdminPlayerReadService(repo)

    detail = await service.get_character_detail(77, inventory_limit=50, inventory_offset=0)

    assert detail is not None
    assert detail.attributes["strength"] == 11
    assert detail.skills == {"skill_swords": 75.0}
    assert detail.free_xp == 12.5
    assert _slot_item(detail.equipment_slots, "main_hand").base_id == "sword-1"
    assert _slot_item(detail.belt_slots, "belt_slot_1").base_id == "potion-1"
    assert detail.carried_total == 2
    assert detail.carried_items[0].base_id == "cloak-1"
    assert detail.carried_items[0].valid_slots == ["outer_garment"]


@pytest.mark.unit
async def test_admin_player_service_returns_none_for_missing_character() -> None:
    service = AdminPlayerReadService(SimpleNamespace(get_character_detail=_missing_character))

    assert await service.get_character_detail(404, inventory_limit=50, inventory_offset=0) is None


def _character(user_id):
    now = datetime(2026, 5, 24, tzinfo=UTC)
    return SimpleNamespace(
        character_id=77,
        user_id=user_id,
        name="Test Hero",
        name_key="test_hero",
        gender="other",
        avatar_url=None,
        game_stage="lobby",
        prev_game_stage=None,
        location_id="start_village",
        created_at=now,
        updated_at=now,
        attributes=SimpleNamespace(
            strength=11,
            agility=10,
            endurance=9,
            intellect=8,
            memory=8,
            mental=8,
            perception=8,
            projection=8,
            prediction=8,
        ),
        skill_progress=[
            SimpleNamespace(skill_key="skill_swords", total_xp=75.0, is_unlocked=True),
            SimpleNamespace(skill_key="skill_locked", total_xp=10.0, is_unlocked=False),
        ],
        progression=SimpleNamespace(free_xp=12.5),
    )


def _item(base_id: str, *, slot: str, tier: int):
    now = datetime(2026, 5, 24, tzinfo=UTC)
    return SimpleNamespace(
        id=f"{base_id}-instance",
        base_id=base_id,
        name=base_id,
        description="",
        item_type="weapon",
        rarity="rare",
        rarity_tier=tier,
        lifecycle_status="active",
        text_status="ready",
        mechanics={"slot": slot, "valid_slots": [slot]},
        metadata_={"source": "test"},
        appearance={},
        generation={"narrative_tags": ["admin-test"]},
        created_at=now,
        updated_at=now,
    )


def _placement(storage_type: str, *, slot: str | None = None, position_index: int | None = None):
    return SimpleNamespace(storage_type=storage_type, slot=slot, position_index=position_index)


def _slot_item(slots, slot_id: str):
    for slot in slots:
        if slot.slot_id == slot_id:
            assert slot.item is not None
            return slot.item
    raise AssertionError(f"slot {slot_id} not found")


async def _missing_character(character_id: int):
    assert character_id == 404
    return None
