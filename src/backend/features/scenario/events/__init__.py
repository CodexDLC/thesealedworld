from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("scenario.start_requested", group="scenario", reply=True)
async def on_scenario_start_requested(payload: dict[str, Any]) -> None:
    # TODO(scenario-migration): activate this path when onboarding moves to event-driven flow.
    # Current monolith onboarding calls ScenarioService directly to avoid self-BLPOP orchestration.
    if _app is None:
        log.warning("Scenario start event ignored: app_not_bound")
        return
    cid = payload.get("correlation_id")

    log.warning("Scenario start event rejected: path_not_wired cid=%s", cid)
    ack: dict[str, Any] = {"status": "error", "error": "scenario.start_requested is not wired yet"}

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Scenario start ack delivery failed: cid=%s", cid)
