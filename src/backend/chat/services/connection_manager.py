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
        self._by_user: dict[str, set[WebSocket]] = defaultdict(set)
        self._user_by_ws: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, topics: list[str], *, user_id: str | None = None) -> None:
        await ws.accept()
        self._by_ws[ws] = set(topics)
        if user_id:
            self._user_by_ws[ws] = user_id
            self._by_user[user_id].add(ws)
        for topic in topics:
            self._by_topic[topic].add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        topics = self._by_ws.pop(ws, set())
        for topic in topics:
            self._by_topic[topic].discard(ws)
            if not self._by_topic[topic]:
                del self._by_topic[topic]
        user_id = self._user_by_ws.pop(ws, None)
        if user_id:
            self._by_user[user_id].discard(ws)
            if not self._by_user[user_id]:
                del self._by_user[user_id]

    def subscribe(self, ws: WebSocket, topic: str) -> None:
        self._by_ws.setdefault(ws, set()).add(topic)
        self._by_topic[topic].add(ws)

    def unsubscribe(self, ws: WebSocket, topic: str) -> None:
        self._by_ws.get(ws, set()).discard(topic)
        self._by_topic[topic].discard(ws)

    def subscribe_user(self, user_id: str, topic: str) -> None:
        for ws in list(self._by_user.get(user_id, [])):
            self.subscribe(ws, topic)

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
