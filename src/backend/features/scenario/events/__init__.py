from __future__ import annotations

import logging
import types
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_session_context
from src.backend.features.scenario.dependencies import build_scenario_service

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


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
    if _app is None:
        log.warning("Scenario start ignored: app_not_bound cid=%s", cid)
        return

    ack: dict[str, Any]
    try:
        char_id = int(payload["char_id"])
        quest_key = str(payload["quest_key"])
        source = str(payload.get("source") or "onboarding")

        async with get_session_context() as db:
            service = build_scenario_service(types.SimpleNamespace(app=_app), db)
            result = await service.initialize(char_id, quest_key, source=source)

        ack = {"status": "ok", "payload": result.model_dump(mode="json")}
    except Exception as exc:
        log.exception("Scenario start_requested failed cid=%s", cid)
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Scenario start ack delivery failed: cid=%s", cid)


@router.on(ScenarioEvents.CLEANUP_REQUESTED, group="scenario", reply=True)
async def on_scenario_cleanup_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Scenario cleanup ignored: app_not_bound cid=%s", cid)
        return

    ack: dict[str, Any]
    try:
        char_id = int(payload["char_id"])

        async with get_session_context() as db:
            service = build_scenario_service(types.SimpleNamespace(app=_app), db)
            await service.cleanup(char_id)

        ack = {"status": "ok"}
    except Exception as exc:
        log.exception("Scenario cleanup_requested failed cid=%s", cid)
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Scenario cleanup ack delivery failed: cid=%s", cid)


__all__ = ["ScenarioEvents", "bind", "router"]
