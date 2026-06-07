"""Unit tests for the realtime WS handler.

The handler in ``src/backend/realtime/api/ws.py`` is intentionally
thin — auth/lock checks, envelope dispatch, htmx unwrap, hot-tail replay.
Each is verified here against a fake WebSocket without spinning up a real
ASGI app, mirroring the pattern used by tests/chat/test_ws.py.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.realtime.api.ws import (
    CODE_AUTH_FAILED,
    CODE_ORIGIN_REJECTED,
    CODE_STALE_SESSION,
    GAME_ACCESS_COOKIE,
    _origin_allowed,
    _parse_envelope,
)


@pytest.mark.unit
def test_parse_envelope_accepts_plain_envelope() -> None:
    envelope = _parse_envelope(json.dumps({"type": "chat.send", "payload": {"channel": "global", "content": "hi"}}))
    assert envelope is not None
    assert envelope.type == "chat.send"


@pytest.mark.unit
def test_parse_envelope_accepts_pong() -> None:
    envelope = _parse_envelope(json.dumps({"type": "pong"}))
    assert envelope is not None
    assert envelope.type == "pong"


@pytest.mark.unit
def test_parse_envelope_unwraps_htmx_form_payload() -> None:
    inner = json.dumps({"type": "chat.send", "payload": {"channel": "global", "content": "hi"}})
    raw = json.dumps({"chat_message": inner, "HEADERS": {"HX-Request": "true"}})

    envelope = _parse_envelope(raw)

    assert envelope is not None
    assert envelope.type == "chat.send"
    assert envelope.payload == {"channel": "global", "content": "hi"}


@pytest.mark.unit
def test_parse_envelope_lifts_bare_chat_dto_from_htmx_wrapper() -> None:
    # Legacy form posted the IncomingMessageDTO shape directly; if any caller
    # still does that, the handler must lift it into the typed envelope rather
    # than silently dropping the message.
    bare = json.dumps({"channel": "zone", "content": "hi", "scope_id": "52_52"})
    raw = json.dumps({"chat_message": bare, "HEADERS": {}})

    envelope = _parse_envelope(raw)

    assert envelope is not None
    assert envelope.type == "chat.send"
    assert envelope.payload["channel"] == "zone"


@pytest.mark.unit
def test_parse_envelope_rejects_malformed_json() -> None:
    assert _parse_envelope("not json") is None


@pytest.mark.unit
def test_parse_envelope_rejects_unknown_type() -> None:
    assert _parse_envelope(json.dumps({"type": "system.shutdown", "payload": {}})) is None


# --- Origin allow-list ---


@pytest.mark.unit
def test_origin_allowed_matches_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.config.settings import settings

    monkeypatch.setattr(settings, "realtime_allowed_origins", ["https://play.example.com"])
    assert _origin_allowed("https://play.example.com") is True
    assert _origin_allowed("https://attacker.example.com") is False
    assert _origin_allowed("") is False
    assert _origin_allowed(None) is False


# --- Auth/lock integration is exercised through the public handler -----------


class _FakeWebSocket:
    def __init__(
        self,
        *,
        origin: str = "http://test.localhost",
        cookies: dict[str, str] | None = None,
    ) -> None:
        self.closed: dict[str, int | str] | None = None
        self.accept_count = 0
        self.sent: list[str] = []
        self.headers = {"origin": origin}
        self.cookies = cookies or {}

    async def accept(self) -> None:
        self.accept_count += 1

    async def send_text(self, data: str) -> None:
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = {"code": code, "reason": reason}


def _allow_test_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.config.settings import settings

    monkeypatch.setattr(settings, "realtime_allowed_origins", ["http://test.localhost"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_origin_rejected_closes_with_4004(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)
    socket = _FakeWebSocket(origin="http://evil.localhost")
    socket.app = SimpleNamespace(state=SimpleNamespace())  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket, token="anything")  # type: ignore[arg-type]

    assert socket.closed == {"code": CODE_ORIGIN_REJECTED, "reason": ""}
    assert socket.accept_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_token_closes_with_4001(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)
    socket = _FakeWebSocket()
    socket.app = SimpleNamespace(state=SimpleNamespace())  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket)  # type: ignore[arg-type]

    assert socket.closed is not None
    assert socket.closed["code"] == CODE_AUTH_FAILED
    # accept() runs before close() so the browser sees the 4001 code instead
    # of a generic 1006 (see _accept_then_close docstring).
    assert socket.accept_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_token_closes_with_4001(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)

    def _raise(_token: str):
        raise ValueError("bad token")

    monkeypatch.setattr(ws_module, "decode_game_access_token", _raise)

    socket = _FakeWebSocket()
    socket.app = SimpleNamespace(state=SimpleNamespace())  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket, token="bad")  # type: ignore[arg-type]

    assert socket.closed is not None
    assert socket.closed["code"] == CODE_AUTH_FAILED
    assert socket.accept_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cookie_token_takes_precedence_over_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production browsers attach the cookie; the URL never carries the token."""
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)

    seen: list[str] = []

    def _capture(token: str):
        seen.append(token)
        raise ValueError("stop after capture")  # bail before app-state work

    monkeypatch.setattr(ws_module, "decode_game_access_token", _capture)

    socket = _FakeWebSocket(cookies={GAME_ACCESS_COOKIE: "cookie-token"})
    socket.app = SimpleNamespace(state=SimpleNamespace())  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket, token="query-token")  # type: ignore[arg-type]

    assert seen == ["cookie-token"]
    assert socket.closed is not None
    assert socket.closed["code"] == CODE_AUTH_FAILED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_token_used_when_cookie_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)

    seen: list[str] = []

    def _capture(token: str):
        seen.append(token)
        raise ValueError("stop after capture")

    monkeypatch.setattr(ws_module, "decode_game_access_token", _capture)

    socket = _FakeWebSocket()
    socket.app = SimpleNamespace(state=SimpleNamespace())  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket, token="query-token")  # type: ignore[arg-type]

    assert seen == ["query-token"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stale_session_closes_with_4003(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)
    fake_claims = SimpleNamespace(sub="user-uuid", character_id=42, session_id="claimed-session")
    monkeypatch.setattr(ws_module, "decode_game_access_token", lambda _t: fake_claims)

    lock = SimpleNamespace(current=AsyncMock(return_value="active-session"))
    state = SimpleNamespace(game_session_lock=lock)
    socket = _FakeWebSocket()
    socket.app = SimpleNamespace(state=state)  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket, token="t")  # type: ignore[arg-type]

    assert socket.closed is not None
    assert socket.closed["code"] == CODE_STALE_SESSION
    # accept-then-close so the client supervisor can react on the 4003 code.
    assert socket.accept_count == 1
    lock.current.assert_awaited_once_with(42)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_token_without_session_id_closes_with_4001(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backend.realtime.api import ws as ws_module

    _allow_test_origin(monkeypatch)
    fake_claims = SimpleNamespace(sub="user-uuid", character_id=42, session_id=None)
    monkeypatch.setattr(ws_module, "decode_game_access_token", lambda _t: fake_claims)

    socket = _FakeWebSocket()
    socket.app = SimpleNamespace(state=SimpleNamespace())  # type: ignore[attr-defined]

    await ws_module.realtime_ws(socket, token="t")  # type: ignore[arg-type]

    assert socket.closed is not None
    assert socket.closed["code"] == CODE_AUTH_FAILED
