from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from loguru import logger

from src.backend.core.bus import GameStreamRouter
from src.backend.features.combat.integrations import CombatSessionIntegration, CombatSystemIntegrator
from src.backend.features.combat.orchestrators import CombatCreationOrchestrator
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService
from src.backend.features.combat.services.loot_preorder_service import CombatLootPreorderService
from src.backend.features.loot.integrations import LootOrderStreamClient

if TYPE_CHECKING:
    from fastapi import FastAPI

router = GameStreamRouter()
_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("combat.session_requested", group="combat")
async def on_session_requested(payload: dict[str, Any]) -> None:
    set_log_context(correlation_id=payload.get("correlation_id"))
    try:
        if _app is None:
            logger.warning("CombatSessionRequestIgnored")
            return

        request_data = dict(payload)
        correlation_id = request_data.get("correlation_id")
        orchestrator = CombatCreationOrchestrator(
            lifecycle=CombatLifecycleService(
                store=CombatSessionIntegration.from_redis(_app.state.redis),
                game_config=getattr(_app.state, "game_config", None),
            ),
            integrator=CombatSystemIntegrator(
                actor_commitments=_app.state.actor_commitments,
                character_sessions=_app.state.character_sessions,
                events=_app.state.events,
                redis=_app.state.redis,
            ),
            loot_preorder=CombatLootPreorderService(LootOrderStreamClient(_app.state.events)),
        )
        try:
            ready = await orchestrator.create_from_request(request_data)
            if correlation_id:
                await _app.state.events.publish_reply(correlation_id, ready, ttl=30)
        except Exception as exc:  # noqa: BLE001
            logger.exception("CombatSessionRequestFailed")
            failed = await orchestrator.fail_request(request_data, f"{exc.__class__.__name__}: {exc}")
            if correlation_id:
                await _app.state.events.publish_reply(correlation_id, failed, ttl=30)
    finally:
        clear_log_context()
