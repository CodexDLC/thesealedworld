import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.infrastructure.actor_state.repositories import InventoryRepository
from sqlalchemy.exc import SQLAlchemyError

@pytest.mark.unit
class TestInventoryRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    async def test_get_items_by_location_batch(self, session):
        repo = InventoryRepository(session)
        mock_item = MagicMock()
        mock_item.id = "i1"
        mock_item.character_id = 1
        mock_item.location = "equipped"
        mock_item.item_type = "weapon"
        mock_item.subtype = "sword"
        mock_item.rarity = "common"
        mock_item.item_data = {}
        mock_item.quantity = 1
        mock_item.equipped_slot = "hand"
        mock_item.quick_slot_position = None

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_item]
        session.scalars = AsyncMock(return_value=mock_result)

        # Mock TypeAdapter
        repo.dto_adapter = MagicMock()
        repo.dto_adapter.validate_python.side_effect = lambda x: x

        result = await repo.get_items_by_location_batch([1], "equipped")
        assert 1 in result
        assert result[1][0]["inventory_id"] == "i1"

    async def test_get_items_by_location_batch_empty(self, session):
        repo = InventoryRepository(session)
        assert await repo.get_items_by_location_batch([], "equipped") == {}

    async def test_get_items_by_location_batch_error(self, session):
        repo = InventoryRepository(session)
        session.scalars = AsyncMock(side_effect=SQLAlchemyError("db fail"))
        with pytest.raises(SQLAlchemyError):
            await repo.get_items_by_location_batch([1], "equipped")
