from __future__ import annotations

from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError


class RedisStreamStorageAdapter:
    """Adapter from redis-py async client to codex-bot stream storage protocol."""

    def __init__(self, client: Redis):
        self.client = client

    async def create_group(self, stream_name: str, group_name: str) -> None:
        try:
            await self.client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def read_events(
        self,
        *,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        response = await self.client.xreadgroup(
            group_name,
            consumer_name,
            streams={stream_name: ">"},
            count=count,
            block=1000,
        )
        return self._flatten(response)

    async def ack_event(self, stream_name: str, group_name: str, message_id: str) -> None:
        await self.client.xack(stream_name, group_name, message_id)

    async def claim_stale_events(
        self,
        *,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        min_idle_time: int,
        count: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        response = await self.client.xautoclaim(
            stream_name,
            group_name,
            consumer_name,
            min_idle_time=min_idle_time,
            start_id="0-0",
            count=count,
        )
        messages = response[1] if len(response) > 1 else []
        return [(self._decode(message_id), self._decode_payload(data)) for message_id, data in messages]

    def _flatten(self, response: Any) -> list[tuple[str, dict[str, Any]]]:
        events: list[tuple[str, dict[str, Any]]] = []
        for _stream, messages in response or []:
            for message_id, data in messages:
                events.append((self._decode(message_id), self._decode_payload(data)))
        return events

    def _decode_payload(self, data: dict[Any, Any]) -> dict[str, Any]:
        return {self._decode(key): self._decode(value) for key, value in data.items()}

    def _decode(self, value: Any) -> Any:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
