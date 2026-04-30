import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from codex_platform.streams import StreamRuntime, StreamRuntimeConfig
from src.backend.config.settings import BackendSettings
from src.backend.core.lifespan import start_event_bus
from src.backend.core.bus.producer import GameEventProducer

@pytest.mark.unit
class TestStreamsMigration:
    @pytest.fixture
    def app(self):
        return FastAPI()

    @pytest.fixture
    def mock_redis(self, mocker):
        mock = MagicMock()
        mocker.patch("redis.asyncio.from_url", return_value=mock)
        return mock

    @pytest.mark.asyncio
    async def test_start_event_bus_monolith(self, app, mock_redis, mocker):
        # Setup settings for monolith
        settings = BackendSettings(
            stream_enabled_groups=None,
            stream_consumer_group="monolith"
        )
        mocker.patch("src.backend.core.lifespan.settings", settings)

        # Mock StreamRuntime to avoid actual start
        mock_runtime_cls = mocker.patch("src.backend.core.lifespan.StreamRuntime")
        mock_runtime = mock_runtime_cls.return_value
        mock_runtime.producer = MagicMock()
        mock_runtime.start = AsyncMock()

        await start_event_bus(app)

        assert hasattr(app.state, "stream_runtime")
        assert isinstance(app.state.events, GameEventProducer)

        # Verify config passed to StreamRuntime
        args, kwargs = mock_runtime_cls.call_args
        config = kwargs["config"]
        assert isinstance(config, StreamRuntimeConfig)
        assert config.consumer_group == "monolith"
        assert config.enabled_groups is None

        # Verify all routers included (checking count based on lifespan.py)
        assert mock_runtime.include_router.call_count == 10

    @pytest.mark.asyncio
    async def test_start_event_bus_partial_group(self, app, mock_redis, mocker):
        # Setup settings for partial group
        settings = BackendSettings(
            stream_enabled_groups=["actor_state"],
            stream_consumer_group="actor_state_service"
        )
        mocker.patch("src.backend.core.lifespan.settings", settings)

        mock_runtime_cls = mocker.patch("src.backend.core.lifespan.StreamRuntime")
        mock_runtime = mock_runtime_cls.return_value
        mock_runtime.producer = MagicMock()
        mock_runtime.start = AsyncMock()

        await start_event_bus(app)

        args, kwargs = mock_runtime_cls.call_args
        config = kwargs["config"]
        assert config.consumer_group == "actor_state_service"
        assert config.enabled_groups == ["actor_state"]

    def test_partial_group_rejects_monolith_group(self):
        # We check BackendSettings because it enforces this constraint
        with pytest.raises(ValueError, match="Partial enabled_groups cannot use 'monolith' consumer group"):
            BackendSettings(
                stream_enabled_groups=["actor_state"],
                stream_consumer_group="monolith"
            )

    @pytest.mark.asyncio
    async def test_request_reply_integration(self, mocker):
        # Test the GameEventProducer.request calling StreamProducer.request
        mock_stream_producer = MagicMock()
        mock_stream_producer.request = AsyncMock(return_value={"status": "ok", "data": 123})
        producer = GameEventProducer(mock_stream_producer)

        response = await producer.request("test.req", {"foo": "bar"}, timeout=10.0)

        assert response == {"status": "ok", "data": 123}
        mock_stream_producer.request.assert_called_once_with(
            "test.req", {"foo": "bar"}, timeout=10.0, correlation_id=None
        )
