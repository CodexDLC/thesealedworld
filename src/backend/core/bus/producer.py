from typing import Any

from codex_platform.streams.producer import StreamProducer


class GameEventProducer:
    """Thin adapter for StreamProducer to maintain backward compatibility."""

    def __init__(self, producer: StreamProducer) -> None:
        self._producer = producer

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        return await self._producer.publish(event_type, data, correlation_id=correlation_id)

    async def request(
        self,
        event_type: str,
        data: dict[str, Any],
        timeout: float = 30.0,
        correlation_id: str | None = None,
    ) -> Any:
        return await self._producer.request(event_type, data, timeout=timeout, correlation_id=correlation_id)

    async def publish_reply(self, correlation_id: str, data: dict[str, Any], ttl: int | None = None) -> None:
        await self._producer.publish_reply(correlation_id, data, ttl=ttl)

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
