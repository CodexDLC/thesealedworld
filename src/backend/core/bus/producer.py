import uuid
from typing import Any

from codex_platform.streams.producer import StreamProducer


class GameEventProducer:
    # TODO(codex-platform): correlation_id support could be upstreamed to StreamProducer.publish()

    def __init__(self, producer: StreamProducer) -> None:
        self._producer = producer

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        payload = {**data}
        if correlation_id:
            payload["correlation_id"] = correlation_id
        return await self._producer.add_event(event_type, payload)

    async def publish_with_correlation(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> tuple[str, str]:
        """Publish event with a fresh correlation_id. Returns (message_id, correlation_id)."""
        cid = str(uuid.uuid4())
        mid = await self.publish(event_type, data, correlation_id=cid)
        return mid, cid
