import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.backend.chat.dto.session import DMMessageDTO, DMSessionDTO, OpenDMSessionRequest
from src.backend.chat.repositories.message_repo import ChatMessageRepository
from src.backend.chat.repositories.session_repo import ChatSessionRepository
from src.backend.core.database import get_session_context
from src.backend.core.security import decode_access_token

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_character_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401)
    try:
        payload = decode_access_token(auth.removeprefix("Bearer ").strip())
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401) from None


@router.get("/history/{channel_type}/{scope_id}")
async def get_history(
    channel_type: str,
    scope_id: str,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    _char_id: str = Depends(_get_character_id),
) -> list[dict]:
    scope = None if scope_id == "null" else scope_id
    async with get_session_context() as session:
        repo = ChatMessageRepository(session)
        messages = await repo.get_history(channel_type, scope, limit=limit, before=before)
    return [
        {
            "id": str(m.id),
            "channel": m.channel_type,
            "scope_id": m.scope_id,
            "sender_id": str(m.sender_id),
            "sender_name": m.sender_name,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(messages)
    ]


@router.get("/dm/sessions")
async def list_dm_sessions(
    character_id: str = Depends(_get_character_id),
) -> list[DMSessionDTO]:
    cid = uuid.UUID(character_id)
    async with get_session_context() as session:
        repo = ChatSessionRepository(session)
        sessions = await repo.get_sessions_for(cid)
    return [
        DMSessionDTO(
            id=str(s.id),
            participant_a_id=str(s.participant_a_id),
            participant_b_id=str(s.participant_b_id),
            created_at=s.created_at,
            last_message_at=s.last_message_at,
        )
        for s in sessions
    ]


@router.post("/dm/sessions")
async def open_dm_session(
    body: OpenDMSessionRequest,
    character_id: str = Depends(_get_character_id),
) -> DMSessionDTO:
    cid = uuid.UUID(character_id)
    async with get_session_context() as session:
        repo = ChatSessionRepository(session)
        dm = await repo.get_or_create(cid, body.target_character_id)
    return DMSessionDTO(
        id=str(dm.id),
        participant_a_id=str(dm.participant_a_id),
        participant_b_id=str(dm.participant_b_id),
        created_at=dm.created_at,
        last_message_at=dm.last_message_at,
    )


@router.get("/dm/sessions/{session_id}/messages")
async def get_dm_messages(
    session_id: uuid.UUID,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    _char_id: str = Depends(_get_character_id),
) -> list[DMMessageDTO]:
    async with get_session_context() as session:
        repo = ChatSessionRepository(session)
        messages = await repo.get_messages(session_id, limit=limit, before=before)
    return [
        DMMessageDTO(
            id=str(m.id),
            session_id=str(m.session_id),
            sender_id=str(m.sender_id),
            content=m.content,
            read_at=m.read_at,
            created_at=m.created_at,
        )
        for m in reversed(messages)
    ]
