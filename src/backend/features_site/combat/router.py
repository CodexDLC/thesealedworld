from __future__ import annotations

import time

from fastapi import APIRouter, Request

from src.backend.infrastructure.combat.managers.session import CombatSessionManager

router = APIRouter(prefix="/api/internal/combat", tags=["combat-internal"])


def _session_manager(request: Request) -> CombatSessionManager:
    return CombatSessionManager(request.app.state.redis)


def _fmt_ts(ts: str | int | None) -> str:
    if not ts:
        return "—"
    try:
        import datetime

        return datetime.datetime.fromtimestamp(int(ts)).strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return str(ts)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict:
    from fastapi import HTTPException

    mgr = _session_manager(request)
    meta = await mgr.get_meta(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, **meta}


@router.get("/sessions")
async def list_active_sessions(request: Request) -> list[dict]:
    mgr = _session_manager(request)
    sessions = await mgr.scan_active_sessions()
    now = int(time.time())
    result = []
    for sid, meta in sessions:
        last_ts = meta.get("last_activity_at")
        idle_sec = (now - int(last_ts)) if last_ts else None
        result.append(
            {
                "session_id": sid,
                "status": meta.get("status", "unknown"),
                "battle_type": meta.get("battle_type", "—"),
                "step": meta.get("step_counter", "0"),
                "alive": meta.get("active_actors_count", "?"),
                "winner": meta.get("winner") or "—",
                "started_at": _fmt_ts(meta.get("started_at")),
                "idle": f"{idle_sec}s" if idle_sec is not None else "—",
            }
        )
    return result
