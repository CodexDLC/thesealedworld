import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.world.services.world_service import WorldService

@pytest.mark.unit
class TestWorldService:
    @pytest.fixture
    def locations(self):
        return MagicMock()

    @pytest.fixture
    def service(self, locations):
        return WorldService(locations)

    async def test_get_location(self, service, locations):
        locations.get_location = AsyncMock(return_value={"id": "l1"})
        assert await service.get_location("l1") == {"id": "l1"}
        locations.get_location.assert_called_with("l1")

    async def test_register_battle(self, service, locations):
        locations.add_battle = AsyncMock()
        await service.register_battle("l1", "b1", "desc")
        locations.add_battle.assert_called_with("l1", "b1", "desc")

    async def test_unregister_battle(self, service, locations):
        locations.remove_battle = AsyncMock()
        await service.unregister_battle("l1", "b1")
        locations.remove_battle.assert_called_with("l1", "b1")
