"""``/ws/realtime`` — the single browser WebSocket per active player session.

Stage 1 carries chat traffic over this transport via ``chat.send`` /
``chat.message`` envelopes. Combat, inventory, exploration, trade, and other
features will publish ``player.notice`` events through this socket in stage 2;
the envelope shape is already in :mod:`src.backend.realtime.dto.envelope`.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger as log
from pydantic import ValidationError

from src.backend.chat.services.message_service import MessageService
from src.backend.core.game_auth import decode_game_access_token
from src.backend.realtime.dto.envelope import IncomingEnvelopeDTO
from src.backend.realtime.services.chat_bridge import ChatBridge, with_session_scope

if TYPE_CHECKING:
    from src.backend.realtime.services.connection_manager import RealtimeConnectionManager

router = APIRouter()

CODE_AUTH_FAILED = 4001
CODE_SESSION_REPLACED = 4002
CODE_STALE_SESSION = 4003

_TAIL_COUNT = 50


@router.websocket("/ws/realtime")
async def realtime_ws(
    ws: WebSocket,
    token: str = Query(...),
    char_id: int | None = Query(default=None),
    combat_session_id: str | None = Query(default=None),
) -> None:
    # 1. Authenticate via game access token.
    try:
        claims = decode_game_access_token(token)
    except Exception:
        await ws.close(code=CODE_AUTH_FAILED)
        return

    if claims.session_id is None:
        await ws.close(code=CODE_AUTH_FAILED, reason="missing session id")
        return

    user_id = str(claims.sub)
    character_id = claims.character_id
    session_id = claims.session_id

    # 2. Enforce single active session (matches HTTP behaviour).
    lock = getattr(ws.app.state, "game_session_lock", None)
    if lock is not None:
        current = await lock.current(character_id)
        if current != session_id:
            await ws.close(code=CODE_STALE_SESSION, reason="stale session")
            return

    realtime_manager: RealtimeConnectionManager = ws.app.state.realtime_manager
    chat_manager = ws.app.state.chat_manager
    redis = ws.app.state.redis
    chat_sessions = ws.app.state.chat_sessions
    msg_service = MessageService(chat_manager, redis)
    bridge = ChatBridge(msg_service)

    # 3. Seed chat session state from the live actor key.
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

    # 4. Build chat topic subscriptions (same set the legacy /ws/chat used).
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

    # 5. Register socket (one accept(), last-wins on character_id).
    entry = await realtime_manager.connect(
        ws,
        user_id=user_id,
        character_id=character_id,
        session_id=session_id,
        topics=topics,
        chat_manager=chat_manager,
    )

    # 6. Replay hot tail for each subscribed channel through the envelope
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

    # 7. Receive loop.
    sender_name: str = state.get("sender_name") or user_id
    try:
        while True:
            raw = await ws.receive_text()
            envelope = _parse_envelope(raw)
            if envelope is None:
                await _send_error(ws, "invalid_envelope")
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

    except WebSocketDisconnect:
        pass
    except Exception:
        log.bind(character_id=character_id).exception("RealtimeReceiveLoopFailed")
    finally:
        realtime_manager.disconnect(ws, chat_manager)


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
        await _send_error(ws, "invalid_message")
        return False

    if msg.channel == "zone" and not msg.scope_id:
        current_state = await chat_sessions.get_state(user_id)
        scoped = with_session_scope(msg, current_state)
        if scoped is None:
            await _send_error(ws, "zone_scope_unavailable")
            return False
        msg = scoped

    try:
        await bridge.handle_chat_send(
            msg.model_dump(),
            sender_id=uuid.UUID(user_id),
            sender_name=sender_name,
        )
    except Exception:
        log.bind(character_id=user_id).exception("RealtimeChatSendFailed")
        return False
    return True


async def _send_error(ws: WebSocket, code: str) -> None:
    try:
        await ws.send_text(json.dumps({"type": "error", "payload": {"code": code}}))
    except Exception:
        log.bind(code=code).debug("RealtimeErrorFrameSendFailed")
