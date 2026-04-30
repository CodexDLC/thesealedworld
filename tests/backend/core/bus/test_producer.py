import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.core.bus.producer import GameEventProducer

@pytest.mark.unit
class TestGameEventProducer:
    @pytest.fixture
    def mock_stream_producer(self):
        return MagicMock()

    @pytest.fixture
    def producer(self, mock_stream_producer):
        return GameEventProducer(mock_stream_producer)

    @pytest.mark.asyncio
    async def test_publish_without_correlation(self, producer, mock_stream_producer):
        mock_stream_producer.publish = AsyncMock(return_value="msg-123")

        mid = await producer.publish("test_event", {"foo": "bar"})

        assert mid == "msg-123"
        mock_stream_producer.publish.assert_called_once_with("test_event", {"foo": "bar"}, correlation_id=None)

    @pytest.mark.asyncio
    async def test_publish_with_explicit_correlation(self, producer, mock_stream_producer):
        mock_stream_producer.publish = AsyncMock(return_value="msg-123")

        mid = await producer.publish("test_event", {"foo": "bar"}, correlation_id="cid-1")

        assert mid == "msg-123"
        mock_stream_producer.publish.assert_called_once_with("test_event", {"foo": "bar"}, correlation_id="cid-1")

    @pytest.mark.asyncio
    async def test_publish_with_generated_correlation(self, producer, mock_stream_producer):
        mock_stream_producer.publish = AsyncMock(return_value="msg-123")

        mid, cid = await producer.publish_with_correlation("test_event", {"foo": "bar"})

        assert mid == "msg-123"
        assert len(cid) == 36 # uuid4
        mock_stream_producer.publish.assert_called_once_with("test_event", {"foo": "bar"}, correlation_id=cid)

    @pytest.mark.asyncio
    async def test_publish_reply(self, producer, mock_stream_producer):
        mock_stream_producer.publish_reply = AsyncMock()

        await producer.publish_reply("cid-1", {"status": "ok"}, ttl=30)

        mock_stream_producer.publish_reply.assert_called_once_with("cid-1", {"status": "ok"}, ttl=30)
