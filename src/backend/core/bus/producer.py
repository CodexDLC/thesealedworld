from typing import Any

from codex_platform.streams.producer import StreamProducer
from loguru import logger


class GameEventProducer:
    """Thin adapter for StreamProducer to maintain backward compatibility."""

    def __init__(self, producer: StreamProducer, *, maxlen: int | None = None) -> None:
        self._producer = producer
        self._maxlen = maxlen

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        message_id = await self._producer.publish(event_type, data, correlation_id=correlation_id)
        await self._trim_stream()
        logger.info("Event published: type={} message_id={} correlation_id={}", event_type, message_id, correlation_id)
        return message_id

    async def request(
        self,
        event_type: str,
        data: dict[str, Any],
        timeout: float = 30.0,
        correlation_id: str | None = None,
    ) -> Any:
        logger.info("Event request started: type={} correlation_id={} timeout={}", event_type, correlation_id, timeout)
        response = await self._producer.request(event_type, data, timeout=timeout, correlation_id=correlation_id)
        logger.info("Event request completed: type={} correlation_id={}", event_type, correlation_id)
        return response

    async def publish_reply(self, correlation_id: str, data: dict[str, Any], ttl: int | None = None) -> None:
        await self._producer.publish_reply(correlation_id, data, ttl=ttl)
        logger.info(
            "Event reply published: correlation_id={} status={} ttl={}", correlation_id, data.get("status"), ttl
        )

    async def publish_with_correlation(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Legacy method.
        Note: StreamProducer.request() is preferred for request-response patterns.
        """
        import uuid

        cid = str(uuid.uuid4())
        mid = await self.publish(event_type, data, correlation_id=cid)
        return mid, cid

    async def _trim_stream(self) -> None:
        if not self._maxlen or self._maxlen <= 0:
            return
        client = getattr(self._producer, "client", None)
        stream_name = getattr(self._producer, "stream_name", None)
        if client is None or stream_name is None:
            return
        await client.xtrim(stream_name, maxlen=self._maxlen, approximate=True)
