from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from codex_platform.streams import StreamRouter
from loguru import logger

from src.backend.core.database.session import get_session_context
from src.backend.features.scenario.dependencies import build_scenario_service

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None


class ScenarioEvents:
    START_REQUESTED = "scenario.start_requested"
    INITIALIZED = "scenario.initialized"
    CLEANUP_REQUESTED = "scenario.cleanup_requested"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(ScenarioEvents.START_REQUESTED, group="scenario", reply=True)
async def on_scenario_start_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    set_log_context(correlation_id=cid)
    try:
        if _app is None:
            logger.warning("ScenarioStartIgnored")
            return

        ack: dict[str, Any]
        try:
            char_id = int(payload["char_id"])
            quest_key = str(payload["quest_key"])
            source = str(payload.get("source") or "onboarding")
            npc_key = str(payload.get("npc_key") or "") or None

            async with get_session_context() as db:
                service = build_scenario_service(types.SimpleNamespace(app=_app), db)
                result = await service.initialize(char_id, quest_key, source=source, npc_key=npc_key)

            ack = {"status": "ok", "payload": result.model_dump(mode="json")}
        except Exception as exc:
            logger.exception("ScenarioStartRequestedFailed")
            ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}

        if cid:
            try:
                await _app.state.events.publish_reply(cid, ack, ttl=30)
            except Exception:
                logger.exception("ScenarioStartAckDeliveryFailed")
    finally:
        clear_log_context()


@router.on(ScenarioEvents.CLEANUP_REQUESTED, group="scenario", reply=True)
async def on_scenario_cleanup_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    set_log_context(correlation_id=cid)
    try:
        if _app is None:
            logger.warning("ScenarioCleanupIgnored")
            return

        ack: dict[str, Any]
        try:
            char_id = int(payload["char_id"])

            async with get_session_context() as db:
                service = build_scenario_service(types.SimpleNamespace(app=_app), db)
                await service.cleanup(char_id)

            ack = {"status": "ok"}
        except Exception as exc:
            logger.exception("ScenarioCleanupRequestedFailed")
            ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}

        if cid:
            try:
                await _app.state.events.publish_reply(cid, ack, ttl=30)
            except Exception:
                logger.exception("ScenarioCleanupAckDeliveryFailed")
    finally:
        clear_log_context()


__all__ = ["ScenarioEvents", "bind", "router"]
