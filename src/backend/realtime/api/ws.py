"""``/ws/realtime`` — the single browser WebSocket per active player session.

Stage 1 carries chat traffic over this transport via ``chat.send`` /
``chat.message`` envelopes. Combat, inventory, exploration, trade, and other
features will publish ``player.notice`` events through this socket in stage 2;
the envelope shape is already in :mod:`src.backend.realtime.dto.envelope`.

Authentication
--------------
The handshake reads ``tbmmorpg_game_access_token`` from cookies. The same
cookie is rotated by :class:`GameTokenRefreshMiddleware` on every game-area
HTTP call (12h refresh window), so a long-lived browser tab survives the 15
minute access expiry without the page knowing the new value. ``?token=`` is
kept as a fallback for diagnostics and tests; in production the browser tab
never has access to the value to embed it in the URL.

Anti-CSWSH
----------
The cookie is sent automatically with cross-origin WS handshakes, so the
handler enforces a strict ``Origin`` allow-list (``settings.realtime_allowed_origins``)
before accepting. Combined with ``SameSite=Lax`` on the token cookie this
gives two independent rejection layers against cross-site hijacking.

Liveness
--------
A background ping task sends ``{"type": "ping"}`` on a fixed interval. The
client must reply with ``{"type": "pong"}``. If two pings pass without a
pong (configurable timeout) the server force-closes the socket so dead NAT
sessions get cleaned up instead of leaking forever.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger as log
from pydantic import ValidationError

from src.backend.chat.services.message_service import MessageService
from src.backend.config.settings import settings
from src.backend.core.game_auth import decode_game_access_token
from src.backend.realtime.dto.envelope import IncomingEnvelopeDTO
from src.backend.realtime.services.chat_bridge import ChatBridge, with_session_scope

if TYPE_CHECKING:
    from src.backend.realtime.services.connection_manager import RealtimeConnectionManager

router = APIRouter()

CODE_AUTH_FAILED = 4001
CODE_SESSION_REPLACED = 4002
CODE_STALE_SESSION = 4003
CODE_ORIGIN_REJECTED = 4004
CODE_HEARTBEAT_TIMEOUT = 4008

GAME_ACCESS_COOKIE = "tbmmorpg_game_access_token"

_TAIL_COUNT = 50


def _origin_allowed(origin: str | None) -> bool:
    """Match the handshake ``Origin`` header against the configured allow-list.

    Returning ``True`` for missing/empty origins would re-open the CSWSH hole
    that the cookie-auth migration was supposed to close — so the answer is
    always ``False`` unless the header is present and an exact string match.
    """
    if not origin:
        return False
    return origin in set(settings.realtime_allowed_origins)


def _extract_token(ws: WebSocket, query_token: str | None) -> str | None:
    """Cookie is authoritative; query token is a diagnostics/test fallback."""
    cookie_value = ws.cookies.get(GAME_ACCESS_COOKIE)
    if cookie_value:
        return cookie_value
    return query_token


@router.websocket("/ws/realtime")
async def realtime_ws(
    ws: WebSocket,
    token: str | None = Query(default=None),
    char_id: int | None = Query(default=None),
    combat_session_id: str | None = Query(default=None),
) -> None:
    # 1. Anti-CSWSH: reject BEFORE accept. We must not give a hostile origin a
    #    live socket — even one immediately closed — so this rejection path is
    #    the only place we use the close-without-accept pattern. Browsers see
    #    HTTP 403 here (close code 1006 on the client) which is intentional:
    #    legitimate clients never hit this branch.
    origin = ws.headers.get("origin")
    if not _origin_allowed(origin):
        log.bind(origin=origin).info("RealtimeOriginRejected")
        await ws.close(code=CODE_ORIGIN_REJECTED)
        return

    # 2. Authenticate via game access token (cookie preferred over query).
    #    For auth-class failures we DO accept first so the client receives the
    #    real close code (4001/4003) — otherwise the browser collapses every
    #    pre-accept close into a generic 1006 and the supervisor cannot
    #    distinguish "refresh the cookie" from "network blip".
    token_value = _extract_token(ws, token)
    if not token_value:
        await _accept_then_close(ws, CODE_AUTH_FAILED, "missing token")
        return
    try:
        claims = decode_game_access_token(token_value)
    except Exception:
        await _accept_then_close(ws, CODE_AUTH_FAILED, "invalid token")
        return

    if claims.session_id is None:
        await _accept_then_close(ws, CODE_AUTH_FAILED, "missing session id")
        return

    user_id = str(claims.sub)
    character_id = claims.character_id
    session_id = claims.session_id

    # 3. Enforce single active session (matches HTTP behaviour).
    lock = getattr(ws.app.state, "game_session_lock", None)
    if lock is not None:
        current = await lock.current(character_id)
        if current != session_id:
            await _accept_then_close(ws, CODE_STALE_SESSION, "stale session")
            return

    realtime_manager: RealtimeConnectionManager = ws.app.state.realtime_manager
    chat_manager = ws.app.state.chat_manager
    redis = ws.app.state.redis
    chat_sessions = ws.app.state.chat_sessions
    msg_service = MessageService(chat_manager, redis)
    bridge = ChatBridge(msg_service)

    # 4. Seed chat session state from the live actor key.
    if char_id is not None:
        try:
            raw = await redis.json().get(
                f"game:ac:{char_id}",
                "$.bio.name",
                "$.location.current",
            )
            if raw:
                names = raw.get("$.bio.name") or []
                locs = raw.get("$.location.current") or []
                if names and names[0]:
                    await chat_sessions.set_sender_name(user_id, names[0])
                if locs and locs[0]:
                    await chat_sessions.set_location(user_id, locs[0])
            await redis.set(f"chat:char_to_user:{char_id}", user_id, ex=3600)
        except Exception:
            log.bind(char_id=char_id).debug("RealtimeChatBootstrapSkipped")

    # 5. Build chat topic subscriptions (same set the legacy /ws/chat used).
    state = await chat_sessions.get_state(user_id)
    location_id: str | None = state.get("location_id")
    party_id: str | None = state.get("party_id")
    dm_sessions: list[str] = state.get("dm_sessions", [])

    topics = ["chat:global", "chat:trade", f"chat:system:{user_id}"]
    if location_id:
        topics.append(f"chat:zone:{location_id}")
    if party_id:
        topics.append(f"chat:party:{party_id}")
    if combat_session_id:
        topics.append(f"chat:combat:{combat_session_id}")
    for sid in dm_sessions:
        topics.append(f"chat:dm:{sid}")

    # 6. Register socket (one accept(), last-wins on character_id).
    entry = await realtime_manager.connect(
        ws,
        user_id=user_id,
        character_id=character_id,
        session_id=session_id,
        topics=topics,
        chat_manager=chat_manager,
    )

    # 7. Replay hot tail for each subscribed channel through the envelope
    #    adapter so every chat payload arrives wrapped as `chat.message`.
    for topic in topics:
        stream_key = f"chat:buffer:{topic}"
        try:
            entries = await redis.xrevrange(stream_key, count=_TAIL_COUNT)
            for _, fields in reversed(entries):
                data = fields.get("data")
                if data is None:
                    continue
                await entry.adapter.send_text(data)
        except Exception:
            log.bind(topic=topic, char_id=char_id).debug("RealtimeHotTailReplayFailed")

    # 8. Heartbeat + receive loop. The heartbeat task lives alongside the
    #    receive loop so a missed pong forces close even if the client never
    #    writes anything.
    sender_name: str = state.get("sender_name") or user_id
    liveness = _Liveness()
    heartbeat_task = asyncio.create_task(_heartbeat_loop(ws, liveness, character_id))
    try:
        while True:
            raw = await ws.receive_text()
            envelope = _parse_envelope(raw)
            if envelope is None:
                await _send_error(ws, "invalid_envelope")
                continue

            if envelope.type == "pong":
                liveness.mark_pong()
                continue

            if envelope.type == "chat.send":
                handled = await _handle_chat_send(
                    bridge=bridge,
                    payload=envelope.payload,
                    user_id=user_id,
                    sender_name=sender_name,
                    chat_sessions=chat_sessions,
                    ws=ws,
                )
                if not handled:
                    continue
            else:
                await _send_error(ws, "unsupported_type")

    except WebSocketDisconnect as exc:
        log.bind(
            character_id=character_id,
            session_id=session_id,
            code=exc.code,
            reason=getattr(exc, "reason", None),
        ).info("RealtimeClientDisconnected")
    except Exception:
        log.bind(character_id=character_id).exception("RealtimeReceiveLoopFailed")
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await heartbeat_task
        realtime_manager.disconnect(ws, chat_manager)


class _Liveness:
    """Tracks the last time we observed a pong (or any client activity)."""

    def __init__(self) -> None:
        self.last_pong_at: float = time.monotonic()

    def mark_pong(self) -> None:
        self.last_pong_at = time.monotonic()


async def _heartbeat_loop(ws: WebSocket, liveness: _Liveness, character_id: int) -> None:
    """Send periodic pings; close the socket if pongs stop coming.

    Runs as a background task; the receive loop cancels it on disconnect.
    """
    interval = max(1.0, float(settings.realtime_ping_interval_seconds))
    timeout = max(interval, float(settings.realtime_ping_timeout_seconds))
    try:
        while True:
            await asyncio.sleep(interval)
            if time.monotonic() - liveness.last_pong_at > timeout:
                log.bind(character_id=character_id).info("RealtimeHeartbeatTimeout")
                with contextlib.suppress(Exception):
                    await ws.close(code=CODE_HEARTBEAT_TIMEOUT, reason="heartbeat timeout")
                return
            try:
                await ws.send_text(json.dumps({"type": "ping"}))
            except Exception:
                # Socket already dead; receive loop will surface this.
                return
    except asyncio.CancelledError:
        raise


def _parse_envelope(raw: str) -> IncomingEnvelopeDTO | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    # HTMX ``ws-send`` wraps form fields: {"chat_message": "...", "HEADERS": {...}}.
    if isinstance(parsed, dict) and "chat_message" in parsed:
        try:
            inner = json.loads(parsed["chat_message"])
        except (json.JSONDecodeError, TypeError):
            return None
        # The legacy chat form posted the bare ``IncomingMessageDTO`` JSON. The
        # stage-1 frontend wraps it in a typed envelope; if a caller still
        # sends the bare shape, lift it into one rather than dropping.
        if isinstance(inner, dict) and inner.get("type") is None and "channel" in inner:
            parsed = {"type": "chat.send", "payload": inner}
        else:
            parsed = inner
    if not isinstance(parsed, dict):
        return None
    try:
        return IncomingEnvelopeDTO.model_validate(parsed)
    except ValidationError:
        return None


async def _handle_chat_send(
    *,
    bridge: ChatBridge,
    payload: dict,
    user_id: str,
    sender_name: str,
    chat_sessions,
    ws: WebSocket,
) -> bool:
    from src.backend.chat.dto.message import IncomingMessageDTO

    try:
        msg = IncomingMessageDTO.model_validate(payload)
    except ValidationError:
        log.bind(sender_id=user_id).warning("RealtimeChatPayloadInvalid")
        await _send_error(ws, "invalid_message")
        return False

    if msg.channel == "zone" and not msg.scope_id:
        current_state = await chat_sessions.get_state(user_id)
        scoped = with_session_scope(msg, current_state)
        if scoped is None:
            log.bind(sender_id=user_id, channel=msg.channel).warning("RealtimeChatScopeUnavailable")
            await _send_error(ws, "zone_scope_unavailable")
            return False
        msg = scoped

    try:
        log.bind(
            sender_id=user_id,
            channel=msg.channel,
            scope_id=msg.scope_id,
            content_length=len(msg.content or ""),
        ).info("RealtimeChatSendReceived")
        await bridge.handle_chat_send(
            msg.model_dump(),
            sender_id=uuid.UUID(user_id),
            sender_name=sender_name,
        )
    except Exception:
        log.bind(sender_id=user_id, channel=msg.channel).exception("RealtimeChatSendFailed")
        return False
    return True


async def _accept_then_close(ws: WebSocket, code: int, reason: str) -> None:
    """Accept the handshake so the browser can surface our 4xxx close code.

    Calling ``ws.close(code=4001)`` before ``accept()`` makes uvicorn return
    HTTP 403 and the browser collapses that into ``CloseEvent.code = 1006``,
    erasing our reason. Accepting first costs one extra TCP roundtrip but
    gives the supervisor JS the signal it needs to drive cookie refresh.
    """
    try:
        await ws.accept()
    except Exception:
        return
    log.info(f"RealtimeAuthClose code={code} reason={reason!r}")
    try:
        await ws.close(code=code, reason=reason)
    except Exception:
        log.bind(code=code).debug("RealtimeAuthCloseFailed")


async def _send_error(ws: WebSocket, code: str) -> None:
    try:
        await ws.send_text(json.dumps({"type": "error", "payload": {"code": code}}))
    except Exception:
        log.bind(code=code).debug("RealtimeErrorFrameSendFailed")
