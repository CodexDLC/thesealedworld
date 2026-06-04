import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.backend.chat.dto.session import DMMessageDTO, DMSessionDTO, OpenDMSessionRequest
from src.backend.chat.repositories.message_repo import ChatThreadRepository
from src.backend.chat.repositories.session_repo import ChatSessionRepository
from src.backend.core.database import get_session_context
from src.backend.core.security import decode_access_token
from src.backend.infrastructure.mongo import ChatBucketRepository, get_mongo_provider

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
    thread_type = (
        "location" if channel_type == "zone" else "world" if channel_type in {"global", "trade"} else channel_type
    )
    if thread_type == "world" and scope is None:
        scope = channel_type
    async with get_session_context() as session:
        repo = ChatThreadRepository(session)
        thread = await repo.get_thread(thread_type=thread_type, scope_id=scope)
        if thread is None:
            return []
        rows = await repo.get_history_index(thread.id, limit=limit, before=before)
    return await _hydrate_history(rows, channel=channel_type, scope_id=scope)


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
            participant_a_id=str(_dm_participants(s)[0]),
            participant_b_id=str(_dm_participants(s)[1]),
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
        participant_a_id=str(_dm_participants(dm)[0]),
        participant_b_id=str(_dm_participants(dm)[1]),
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
        repo = ChatThreadRepository(session)
        messages = await repo.get_history_index(session_id, limit=limit, before=before)
    hydrated = await _hydrate_history(messages, channel="dm", scope_id=str(session_id))
    return [
        DMMessageDTO(
            id=str(m["id"]),
            session_id=str(session_id),
            sender_id=str(m["sender_id"]),
            content=str(m.get("content") or ""),
            read_at=None,
            created_at=datetime.fromisoformat(str(m["created_at"])),
        )
        for m in hydrated
    ]


async def _hydrate_history(rows, *, channel: str, scope_id: str | None) -> list[dict]:
    ordered = list(reversed(rows))
    mongo_repo = ChatBucketRepository(get_mongo_provider().database())
    refs = [
        (row.mongo_collection, row.mongo_bucket_id, row.bucket_seq)
        for row in ordered
        if row.mongo_collection and row.mongo_bucket_id and row.bucket_seq is not None
    ]
    bodies = await mongo_repo.get_messages(refs)
    result: list[dict] = []
    for row in ordered:
        body = bodies.get((row.mongo_collection, row.mongo_bucket_id, int(row.bucket_seq or 0))) or {}
        result.append(
            {
                "id": str(row.message_id),
                "channel": channel,
                "scope_id": scope_id,
                "sender_id": str(row.sender_id),
                "sender_name": str((body.get("meta") or {}).get("sender_name") or ""),
                "content": str(body.get("content") or ""),
                "created_at": row.created_at.isoformat(),
                "template": body.get("template"),
                "variables": body.get("variables") or {},
                "result": body.get("result") or {},
                "presentation": body.get("presentation") or {},
                "meta": body.get("meta") or {},
            }
        )
    return result


def _dm_participants(thread) -> tuple[uuid.UUID, uuid.UUID]:
    ids = sorted(member.character_id for member in thread.members)
    if len(ids) >= 2:
        return ids[0], ids[1]
    empty = uuid.UUID(int=0)
    return (ids[0], empty) if ids else (empty, empty)
