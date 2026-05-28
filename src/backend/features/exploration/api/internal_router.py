from __future__ import annotations

from fastapi import APIRouter, Request

from src.backend.infrastructure.exploration.managers import ExplorationEncounterRuntimeManager

router = APIRouter(prefix="/api/internal/exploration", tags=["exploration-internal"])


@router.get("/sessions")
async def list_encounter_sessions(request: Request) -> list[dict]:
    return await ExplorationEncounterRuntimeManager(request.app.state.redis).list_session_summaries()
