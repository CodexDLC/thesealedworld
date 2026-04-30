import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.world.services.cache_service import WorldCacheService

@pytest.mark.unit
class TestWorldCacheService:
    @pytest.fixture
    def repository(self):
        return MagicMock()

    @pytest.fixture
    def locations(self):
        return MagicMock()

    @pytest.fixture
    def navigation(self):
        return MagicMock()

    @pytest.fixture
    def service(self, repository, locations, navigation):
        return WorldCacheService(repository, locations, navigation)

    async def test_warm_runtime_cache(self, service, repository, locations):
        node = MagicMock(x=52, y=52, content={"title": "T1"}, flags={}, services=[], zone_id="z1", terrain_type="t1")
        repository.get_active_nodes = AsyncMock(return_value=[node])
        locations.write_locations = AsyncMock(return_value=1)

        count = await service.warm_runtime_cache()
        assert count == 1
        locations.write_locations.assert_called_once()

    def test_to_location_cache_with_defaults(self, service, navigation):
        node = MagicMock(x=52, y=52, content=None, flags=None, services=None, zone_id="z1", terrain_type="t1")
        navigation.calculate_exits.return_value = {"exit1": {}}

        cache = service._to_location_cache(node, {})
        assert cache["loc_id"] == "52_52"
        assert cache["name"] == "Узел 52_52"
        assert cache["description"] == "..."
        assert cache["services"] == []

    def test_to_location_cache_full(self, service, navigation):
        node = MagicMock(
            x=52, y=52,
            content={"title": "Title", "description": "Desc", "environment_tags": ["tag1"]},
            flags={"f1": True},
            services=["s1"],
            zone_id="z1",
            terrain_type="t1"
        )
        navigation.calculate_exits.return_value = {}

        cache = service._to_location_cache(node, {})
        assert cache["name"] == "Title"
        assert cache["description"] == "Desc"
        assert cache["tags"] == ["tag1"]
        assert cache["service"] == "s1"
        assert cache["services"] == ["s1"]
        assert cache["flags"] == {"f1": True}
