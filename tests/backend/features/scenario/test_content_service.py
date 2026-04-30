import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.scenario.services.content_service import ScenarioContentService

@pytest.mark.unit
class TestScenarioContentService:
    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def redis(self):
        mock = MagicMock()
        mock.hash = MagicMock()
        mock.string = MagicMock()
        return mock

    @pytest.fixture
    def service(self, repo, redis):
        return ScenarioContentService(repo, redis)

    async def test_get_master_cached(self, service, redis):
        data = {"quest_key": "q1", "start_node_id": "n1"}
        redis.hash.get_field = AsyncMock(return_value=json.dumps(data))

        result = await service.get_master("q1")
        assert result["quest_key"] == "q1"
        redis.hash.get_field.assert_called_once()

    async def test_get_master_not_cached(self, service, repo, redis):
        data = {"quest_key": "q1", "start_node_id": "n1"}
        redis.hash.get_field = AsyncMock(return_value=None)
        repo.get_master = AsyncMock(return_value=data)
        redis.hash.set_field = AsyncMock()
        redis.string.expire = AsyncMock()

        result = await service.get_master("q1")
        assert result["quest_key"] == "q1"
        repo.get_master.assert_called_once()
        redis.hash.set_field.assert_called_once()

    async def test_get_master_not_found(self, service, repo, redis):
        redis.hash.get_field = AsyncMock(return_value=None)
        repo.get_master = AsyncMock(return_value=None)

        result = await service.get_master("unknown")
        assert result is None

    async def test_get_node_cached(self, service, redis):
        data = {"node_key": "n1", "quest_key": "q1"}
        redis.hash.get_field = AsyncMock(return_value=json.dumps(data))

        result = await service.get_node("q1", "n1")
        assert result["node_key"] == "n1"

    async def test_get_node_not_cached(self, service, repo, redis):
        data = {"node_key": "n1", "quest_key": "q1"}
        redis.hash.get_field = AsyncMock(return_value=None)
        repo.get_node = AsyncMock(return_value=data)
        redis.hash.set_field = AsyncMock()
        redis.string.expire = AsyncMock()

        result = await service.get_node("q1", "n1")
        assert result["node_key"] == "n1"

    async def test_get_node_not_found(self, service, repo, redis):
        redis.hash.get_field = AsyncMock(return_value=None)
        repo.get_node = AsyncMock(return_value=None)

        result = await service.get_node("q1", "unknown")
        assert result is None

    async def test_get_nodes_by_pool(self, service, repo):
        data = {"node_key": "n1", "quest_key": "q1"}
        repo.get_nodes_by_pool = AsyncMock(return_value=[data])
        result = await service.get_nodes_by_pool("q1", "tag")
        assert len(result) == 1
        assert result[0]["node_key"] == "n1"

    async def test_invalidate(self, service, redis):
        redis.string.delete = AsyncMock()
        await service.invalidate("q1")
        redis.string.delete.assert_called_once()
