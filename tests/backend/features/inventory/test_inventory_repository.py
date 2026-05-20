from __future__ import annotations

import pytest

from src.backend.features.inventory.repositories.items import InventoryItemRepository
from src.backend.features.items.models import ItemPlacement, ItemTransaction


class FakeSession:
    def __init__(self, placement: ItemPlacement | None) -> None:
        self.placement = placement
        self.added: list[object] = []
        self.flushed = False

    async def scalar(self, _stmt):
        return self.placement

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.unit
async def test_discard_character_item_moves_placement_to_system_and_records_transaction():
    placement = ItemPlacement(
        item_id="item-1",
        holder_type="character",
        holder_id="7",
        storage_type="backpack",
        slot="main_hand",
        position_index=2,
        locked_by="inventory",
    )
    session = FakeSession(placement)
    repository = InventoryItemRepository(session)

    discarded = await repository.discard_character_item(7, "item-1")

    transaction = next(value for value in session.added if isinstance(value, ItemTransaction))
    assert discarded is True
    assert session.flushed is True
    assert placement.holder_type == "system"
    assert placement.holder_id == "discarded:7"
    assert placement.storage_type == "discarded"
    assert placement.slot is None
    assert placement.position_index is None
    assert placement.locked_by is None
    assert transaction.item_id == "item-1"
    assert transaction.from_holder_type == "character"
    assert transaction.from_holder_id == "7"
    assert transaction.from_storage_type == "backpack"
    assert transaction.to_holder_type == "system"
    assert transaction.to_holder_id == "discarded:7"
    assert transaction.to_storage_type == "discarded"
    assert transaction.reason == "inventory_drop"


@pytest.mark.unit
async def test_discard_character_item_returns_false_when_placement_is_missing():
    session = FakeSession(None)
    repository = InventoryItemRepository(session)

    discarded = await repository.discard_character_item(7, "missing")

    assert discarded is False
    assert session.added == []
    assert session.flushed is False


@pytest.mark.unit
async def test_discard_character_item_supports_active_expedition_placement():
    placement = ItemPlacement(
        item_id="item-1",
        holder_type="expedition",
        holder_id="run-1",
        storage_type="backpack",
        slot=None,
    )
    session = FakeSession(placement)
    repository = InventoryItemRepository(session)

    discarded = await repository.discard_character_item(7, "item-1", expedition_run_id="run-1")

    transaction = next(value for value in session.added if isinstance(value, ItemTransaction))
    assert discarded is True
    assert transaction.from_holder_type == "expedition"
    assert transaction.from_holder_id == "run-1"
    assert placement.holder_type == "system"
    assert placement.holder_id == "discarded:7"
