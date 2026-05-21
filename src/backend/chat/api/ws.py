import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger as log

from src.backend.chat.dto.message import IncomingMessageDTO
from src.backend.chat.services.message_service import MessageService
from src.backend.core.security import decode_access_token

router = APIRouter()

_TAIL_COUNT = 50


def _with_session_scope(msg: IncomingMessageDTO, state: dict) -> IncomingMessageDTO | None:
    if msg.channel != "zone" or msg.scope_id:
        return msg

    location_id = state.get("location_id")
    if not location_id:
        return None
    return msg.model_copy(update={"scope_id": str(location_id)})


@router.websocket("/ws/chat")
async def chat_ws(
    ws: WebSocket,
    token: str = Query(...),
    char_id: int | None = Query(default=None),
    combat_session_id: str | None = Query(default=None),
) -> None:
    # 1. Authenticate
    try:
        payload = decode_access_token(token)
        character_id: str = payload["sub"]
    except Exception:
        await ws.close(code=4001)
        return

    manager = ws.app.state.chat_manager
    redis = ws.app.state.redis
    chat_sessions = ws.app.state.chat_sessions
    msg_service = MessageService(manager, redis)

    # 2. Bootstrap chat session state from backend actor key game:ac:{char_id}
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
                    await chat_sessions.set_sender_name(character_id, names[0])
                if locs and locs[0]:
                    await chat_sessions.set_location(character_id, locs[0])
            # Store reverse mapping char_id → user_uuid for location_changed events
            await redis.set(f"chat:char_to_user:{char_id}", character_id, ex=3600)
        except Exception:
            log.bind(char_id=char_id).debug("ChatBootstrapSkipped")

    # 3. Load hot session state
    state = await chat_sessions.get_state(character_id)
    location_id: str | None = state.get("location_id")
    party_id: str | None = state.get("party_id")
    dm_sessions: list[str] = state.get("dm_sessions", [])

    # 4. Build topics to subscribe
    topics = ["chat:global", "chat:trade", f"chat:system:{character_id}"]
    if location_id:
        topics.append(f"chat:zone:{location_id}")
    if party_id:
        topics.append(f"chat:party:{party_id}")
    if combat_session_id:
        topics.append(f"chat:combat:{combat_session_id}")
    for sid in dm_sessions:
        topics.append(f"chat:dm:{sid}")

    # 5. Register connection
    await manager.connect(ws, topics, user_id=character_id)

    # 6. Send hot tail for each subscribed channel from Redis Streams
    for topic in topics:
        stream_key = f"chat:buffer:{topic}"
        try:
            entries = await redis.xrevrange(stream_key, count=_TAIL_COUNT)
            for _, fields in reversed(entries):
                await ws.send_text(fields.get("data", "{}"))
        except Exception:
            pass

    # 7. Receive loop
    sender_name: str = state.get("sender_name", character_id)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                parsed = json.loads(raw)
                # htmx ws-send wraps form fields: {"chat_message": "...", "HEADERS": {...}}
                if isinstance(parsed, dict) and "chat_message" in parsed:
                    msg = IncomingMessageDTO.model_validate_json(parsed["chat_message"])
                else:
                    msg = IncomingMessageDTO.model_validate(parsed)
            except Exception:
                await ws.send_text(json.dumps({"error": "invalid_message"}))
                continue

            if msg.channel == "zone" and not msg.scope_id:
                current_state = await chat_sessions.get_state(character_id)
                scoped_msg = _with_session_scope(msg, current_state)
                if scoped_msg is None:
                    await ws.send_text(json.dumps({"error": "zone_scope_unavailable"}))
                    continue
                msg = scoped_msg

            try:
                await msg_service.handle_incoming(msg, uuid.UUID(character_id), sender_name)
            except Exception:
                log.bind(character_id=character_id).exception("ChatMessageHandleFailed")

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
