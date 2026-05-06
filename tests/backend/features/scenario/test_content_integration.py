from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.scenario.integrations.content_integration import ScenarioContentIntegration


@pytest.mark.unit
class TestScenarioContentIntegration:
    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def cache(self):
        mock = MagicMock()
        mock.exists = AsyncMock(return_value=False)
        mock.get_all_nodes = AsyncMock(return_value=[])
        mock.cache_quest_data = AsyncMock()
        mock.invalidate = AsyncMock()
        return mock

    @pytest.fixture
    def content(self, repo, cache):
        return ScenarioContentIntegration(repo, cache)

    async def test_get_master_cached(self, content, repo, cache):
        cache.get_master = AsyncMock(return_value={"quest_key": "q1", "start_node_id": "n1"})

        result = await content.get_master("q1")

        assert result["quest_key"] == "q1"
        cache.get_master.assert_awaited_once_with("q1")
        repo.get_master.assert_not_called()

    async def test_get_master_not_cached(self, content, repo, cache):
        cache.get_master = AsyncMock(side_effect=[None, {"quest_key": "q1", "start_node_id": "n1"}])
        repo.get_master = AsyncMock(return_value={"quest_key": "q1", "start_node_id": "n1"})
        repo.get_all_quest_nodes = AsyncMock(return_value=[])

        result = await content.get_master("q1")

        assert result["quest_key"] == "q1"
        repo.get_master.assert_awaited_once_with("q1")
        cache.cache_quest_data.assert_awaited_once()

    async def test_get_master_not_found(self, content, repo, cache):
        cache.get_master = AsyncMock(return_value=None)
        repo.get_master = AsyncMock(return_value=None)

        result = await content.get_master("unknown")

        assert result is None

    async def test_get_node_cached(self, content, repo, cache):
        cache.get_node = AsyncMock(return_value={"node_key": "n1", "quest_key": "q1"})

        result = await content.get_node("q1", "n1")

        assert result["node_key"] == "n1"
        repo.get_master.assert_not_called()

    async def test_get_node_not_cached(self, content, repo, cache):
        cache.get_node = AsyncMock(side_effect=[None, {"node_key": "n1", "quest_key": "q1"}])
        repo.get_master = AsyncMock(return_value={"quest_key": "q1", "start_node_id": "n1"})
        repo.get_all_quest_nodes = AsyncMock(return_value=[{"node_key": "n1", "quest_key": "q1"}])

        result = await content.get_node("q1", "n1")

        assert result["node_key"] == "n1"
        repo.get_all_quest_nodes.assert_awaited_once_with("q1")

    async def test_get_node_not_found(self, content, repo, cache):
        cache.get_node = AsyncMock(return_value=None)
        repo.get_master = AsyncMock(return_value=None)

        result = await content.get_node("q1", "unknown")

        assert result is None

    async def test_get_nodes_by_pool(self, content, repo):
        repo.get_master = AsyncMock(return_value={"quest_key": "q1", "start_node_id": "n1"})
        repo.get_all_quest_nodes = AsyncMock(return_value=[])
        repo.get_nodes_by_pool = AsyncMock(return_value=[{"node_key": "n1", "quest_key": "q1"}])

        result = await content.get_nodes_by_pool("q1", "tag")

        assert len(result) == 1
        assert result[0]["node_key"] == "n1"

    async def test_warm_up_cache_refreshes_existing_cache_from_repo(self, content, repo, cache):
        cache.exists = AsyncMock(return_value=True)
        repo.get_master = AsyncMock(return_value={"quest_key": "q1", "start_node_id": "n1"})
        repo.get_all_quest_nodes = AsyncMock(return_value=[{"node_key": "n1", "quest_key": "q1"}])

        result = await content.warm_up_cache("q1")

        assert result == 1
        repo.get_master.assert_awaited_once_with("q1")
        repo.get_all_quest_nodes.assert_awaited_once_with("q1")
        cache.cache_quest_data.assert_awaited_once()

    async def test_invalidate(self, content, cache):
        await content.invalidate("q1")

        cache.invalidate.assert_awaited_once_with("q1")
