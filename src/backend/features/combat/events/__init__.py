from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.core.bus import GameStreamRouter
from src.backend.features.combat.integrations import CombatSessionIntegration, CombatSystemIntegrator
from src.backend.features.combat.orchestrators import CombatCreationOrchestrator
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService

if TYPE_CHECKING:
    from fastapi import FastAPI

router = GameStreamRouter()
_app: FastAPI | None = None
CHAOS_FIRST_CHECK_DELAY_SECONDS = 300


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("combat.session_requested", group="combat")
async def on_session_requested(payload: dict[str, Any]) -> None:
    if _app is None:
        logger.warning("Combat session request ignored: app_not_bound")
        return

    request_data = dict(payload)
    correlation_id = request_data.get("correlation_id")
    orchestrator = CombatCreationOrchestrator(
        lifecycle=CombatLifecycleService(store=CombatSessionIntegration.from_redis(_app.state.redis)),
        integrator=CombatSystemIntegrator(
            actor_commitments=_app.state.actor_commitments,
            character_sessions=_app.state.character_sessions,
            events=_app.state.events,
            redis=_app.state.redis,
        ),
    )
    try:
        ready = await orchestrator.create_from_request(request_data)
        await _enqueue_chaos_watchdog(ready)
        if correlation_id:
            await _app.state.events.publish_reply(correlation_id, ready, ttl=30)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Combat session request failed")
        failed = await orchestrator.fail_request(request_data, f"{exc.__class__.__name__}: {exc}")
        if correlation_id:
            await _app.state.events.publish_reply(correlation_id, failed, ttl=30)


async def _enqueue_chaos_watchdog(ready: dict[str, Any]) -> None:
    if _app is None:
        return

    combat_id = ready.get("combat_id")
    if not combat_id:
        return

    arq = getattr(_app.state, "combat_arq", None)
    if arq is None:
        logger.warning("Combat chaos watchdog skipped: combat_arq_not_configured combat_id={}", combat_id)
        return

    await arq.enqueue_job(
        "chaos_check_task",
        str(combat_id),
        _defer_until=datetime.now(UTC) + timedelta(seconds=CHAOS_FIRST_CHECK_DELAY_SECONDS),
    )
