from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.infrastructure.scenario.managers.session_manager import (
    SCENARIO_SESSION_TTL_SECONDS,
    ScenarioSessionAlreadyExistsError,
    ScenarioSessionManager,
)


@pytest.mark.unit
class TestScenarioSessionManager:
    @pytest.fixture
    def redis(self):
        mock = MagicMock()
        mock.json_module = AsyncMock()
        mock.string = AsyncMock()
        mock.redis_client = MagicMock()
        return mock

    @pytest.fixture
    def manager(self, redis):
        return ScenarioSessionManager(redis)

    @pytest.fixture
    def context_dto(self):
        return ScenarioContextDTO(
            quest_key="q1",
            current_node_key="n1",
        )

    async def test_create_success(self, manager, redis, context_dto):
        redis.json_module.set.return_value = "OK"
        await manager.create(1, context_dto)
        redis.json_module.set.assert_called_once()
        redis.string.expire.assert_awaited_once_with(manager.build_key(1), SCENARIO_SESSION_TTL_SECONDS)

    async def test_create_already_exists(self, manager, redis, context_dto):
        redis.json_module.set.return_value = None
        with pytest.raises(ScenarioSessionAlreadyExistsError):
            await manager.create(1, context_dto)

    async def test_get_found(self, manager, redis, context_dto):
        redis.json_module.get.return_value = [context_dto.model_dump(mode="json")]
        result = await manager.get(1)
        assert result.quest_key == "q1"

    async def test_get_not_found(self, manager, redis):
        redis.json_module.get.return_value = []
        result = await manager.get(1)
        assert result is None

    async def test_patch(self, manager, redis):
        # Mock pipeline
        mock_json = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock()
        mock_pipe.json.return_value = mock_json

        # Pipeline context manager
        redis.redis_client.pipeline.return_value.__aenter__.return_value = mock_pipe

        await manager.patch(1, {"$.hp": 10})
        mock_json.set.assert_called_once()
        mock_pipe.expire.assert_called_once_with(manager.build_key(1), SCENARIO_SESSION_TTL_SECONDS)
        mock_pipe.execute.assert_called_once()

    async def test_patch_empty(self, manager, redis):
        await manager.patch(1, {})
        redis.redis_client.pipeline.assert_not_called()

    async def test_delete(self, manager, redis):
        await manager.delete(1)
        redis.string.delete.assert_called_once()

    async def test_exists(self, manager, redis):
        redis.string.exists.return_value = True
        assert await manager.exists(1) is True
        redis.string.exists.assert_called_once()

    def test_first_helper(self):
        assert ScenarioSessionManager._first([10]) == 10
        assert ScenarioSessionManager._first([]) is None
        assert ScenarioSessionManager._first(5) == 5

    def test_redis_client_fallback(self, redis):
        # Test the fallback in _redis_client when hasattr fails
        del redis.redis_client
        redis.pipeline.client = "fallback"
        manager = ScenarioSessionManager(redis)
        assert manager._redis_client() == "fallback"
