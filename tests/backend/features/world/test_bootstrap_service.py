import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.world.services.bootstrap_service import WorldBootstrapService

@pytest.mark.unit
class TestWorldBootstrapService:
    @pytest.fixture
    def repository(self):
        return MagicMock()

    @pytest.fixture
    def cache(self):
        return MagicMock()

    @pytest.fixture
    def generator(self):
        return MagicMock()

    @pytest.fixture
    def service(self, repository, cache, generator):
        return WorldBootstrapService(repository, cache, generator)

    async def test_bootstrap_no_data_no_gen(self, service, repository):
        repository.has_world_data = AsyncMock(return_value=False)
        service.auto_generate = False
        service.generator = None

        count = await service.bootstrap()
        assert count == 0

    async def test_bootstrap_no_data_with_gen(self, service, repository, generator, cache):
        repository.has_world_data = AsyncMock(return_value=False)
        service.auto_generate = True
        generator.run = AsyncMock()
        repository.count_active_nodes = AsyncMock(return_value=1)
        cache.warm_runtime_cache = AsyncMock(return_value=1)

        count = await service.bootstrap()
        assert count == 1
        generator.run.assert_called_once()

    async def test_bootstrap_no_active_nodes(self, service, repository):
        repository.has_world_data = AsyncMock(return_value=True)
        repository.count_active_nodes = AsyncMock(return_value=0)
        service.generator = None

        count = await service.bootstrap()
        assert count == 0

    async def test_bootstrap_success(self, service, repository, cache, generator):
        repository.has_world_data = AsyncMock(return_value=True)
        repository.count_active_nodes = AsyncMock(return_value=10)
        cache.warm_runtime_cache = AsyncMock(return_value=10)
        generator.run = AsyncMock()

        count = await service.bootstrap()
        assert count == 10
        generator.run.assert_called_once_with("test")
        cache.warm_runtime_cache.assert_called_once()

    async def test_bootstrap_loads_static_seed_when_world_missing(self, service, repository, cache, generator):
        repository.has_world_data = AsyncMock(return_value=False)
        repository.count_active_nodes = AsyncMock(return_value=25)
        cache.warm_runtime_cache = AsyncMock(return_value=25)
        generator.run = AsyncMock()

        count = await service.bootstrap()

        assert count == 25
        generator.run.assert_called_once_with("test")
