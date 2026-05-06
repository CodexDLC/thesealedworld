import json
import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ChatConnectionManager:
    """In-memory WebSocket registry with direct fan-out — L2World pattern."""

    def __init__(self) -> None:
        self._by_topic: dict[str, set[WebSocket]] = defaultdict(set)
        self._by_ws: dict[WebSocket, set[str]] = {}

    async def connect(self, ws: WebSocket, topics: list[str]) -> None:
        await ws.accept()
        self._by_ws[ws] = set(topics)
        for topic in topics:
            self._by_topic[topic].add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        topics = self._by_ws.pop(ws, set())
        for topic in topics:
            self._by_topic[topic].discard(ws)
            if not self._by_topic[topic]:
                del self._by_topic[topic]

    def subscribe(self, ws: WebSocket, topic: str) -> None:
        self._by_ws.setdefault(ws, set()).add(topic)
        self._by_topic[topic].add(ws)

    def unsubscribe(self, ws: WebSocket, topic: str) -> None:
        self._by_ws.get(ws, set()).discard(topic)
        self._by_topic[topic].discard(ws)

    async def broadcast_topic(self, topic: str, payload: dict) -> None:
        sockets = list(self._by_topic.get(topic, []))
        if not sockets:
            return
        data = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
