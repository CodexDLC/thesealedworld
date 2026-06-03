import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ChatConnectionManager:
    """In-memory WebSocket registry with direct fan-out — L2World pattern.

    Sinks are duck-typed: anything with ``async send_text(str)``. This lets the
    realtime gateway register an envelope-wrapping adapter alongside real
    FastAPI ``WebSocket`` objects without changing fan-out semantics.
    """

    def __init__(self) -> None:
        self._by_topic: dict[str, set[Any]] = defaultdict(set)
        self._by_ws: dict[Any, set[str]] = {}
        self._by_user: dict[str, set[Any]] = defaultdict(set)
        self._user_by_ws: dict[Any, str] = {}

    async def connect(self, ws: WebSocket, topics: list[str], *, user_id: str | None = None) -> None:
        await ws.accept()
        self.register(ws, topics, user_id=user_id)

    def register(self, sink: Any, topics: list[str], *, user_id: str | None = None) -> None:
        """Register an already-accepted socket (or adapter) into topic indexes.

        Does not call ``accept()`` — used by the realtime gateway to attach a
        ``ChatEnvelopeAdapter`` whose underlying WebSocket was already accepted
        by ``RealtimeConnectionManager``.
        """
        self._by_ws[sink] = set(topics)
        if user_id:
            self._user_by_ws[sink] = user_id
            self._by_user[user_id].add(sink)
        for topic in topics:
            self._by_topic[topic].add(sink)

    def disconnect(self, ws: Any) -> None:
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

    def unregister(self, sink: Any) -> None:
        """Drop a sink from topic indexes without closing it.

        Same effect as :meth:`disconnect`; the alias makes the semantic split
        explicit when the caller owns the close (e.g. the realtime gateway
        closes the real WebSocket separately from cleaning up the adapter).
        """
        self.disconnect(sink)

    def subscribe(self, ws: Any, topic: str) -> None:
        self._by_ws.setdefault(ws, set()).add(topic)
        self._by_topic[topic].add(ws)

    def unsubscribe(self, ws: Any, topic: str) -> None:
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
        dead: list[Any] = []
        for ws in sockets:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
