from __future__ import annotations

from typing import Any


class FakeWebSocket:
    """Minimal stand-in for ``fastapi.WebSocket`` used in unit tests.

    Records ``accept`` / ``send_text`` / ``close`` calls so tests can assert
    that the realtime manager and chat envelope adapter behave correctly.
    """

    def __init__(self) -> None:
        self.accept_count: int = 0
        self.sent: list[str] = []
        self.closed: dict[str, Any] | None = None
        self.send_raises: BaseException | None = None
        self.close_raises: BaseException | None = None
        self.accept_raises: BaseException | None = None

    async def accept(self) -> None:
        if self.accept_raises is not None:
            raise self.accept_raises
        self.accept_count += 1

    async def send_text(self, data: str) -> None:
        if self.send_raises is not None:
            raise self.send_raises
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if self.close_raises is not None:
            raise self.close_raises
        self.closed = {"code": code, "reason": reason}
