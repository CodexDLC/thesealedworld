from __future__ import annotations

from fastapi import APIRouter, Request

from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager

router = APIRouter(prefix="/api/internal/scenario", tags=["scenario-internal"])


@router.get("/sessions")
async def list_scenario_sessions(request: Request) -> list[dict]:
    return await ScenarioSessionManager(request.app.state.redis).list_session_summaries()
