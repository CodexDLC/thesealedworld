from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context

from src.backend.core.bus import GameStreamRouter
from src.backend.core.database import get_session_context
from src.backend.features.rift.integrations import RiftRuntimeIntegration
from src.backend.features.rift.services import RiftEntryService
from src.backend.infrastructure.rift.managers import (
    RiftInstanceStore,
    RiftPortalStore,
    RiftPresenceStore,
    RiftRunSessionStore,
)
from src.backend.infrastructure.rift.repositories import (
    RiftInstanceStateRepository,
    RiftPortalKeyRepository,
    RiftRunStateRepository,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

router = GameStreamRouter()
_app: FastAPI | None = None


class RiftEvents:
    ENTRY_REQUESTED = "rift.entry_requested"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(RiftEvents.ENTRY_REQUESTED, group="rift", reply=True)
async def on_entry_requested(payload: dict[str, Any]) -> None:
    set_log_context(correlation_id=payload.get("correlation_id"))
    try:
        if _app is None:
            return
        async with get_session_context() as session:
            ack = await _entry_service(_app, session).handle_entry_requested(payload)
        if payload.get("correlation_id"):
            await _app.state.events.publish_reply(str(payload["correlation_id"]), ack, ttl=30)
    finally:
        clear_log_context()


def _entry_service(app: FastAPI, session: Any) -> RiftEntryService:
    return RiftEntryService(
        runtime=RiftRuntimeIntegration(
            instance_store=RiftInstanceStore(app.state.redis),
            session_store=RiftRunSessionStore(app.state.redis),
            presence_store=RiftPresenceStore(app.state.redis),
            portal_store=RiftPortalStore(app.state.redis),
            instance_state_repository=RiftInstanceStateRepository(session),
            run_state_repository=RiftRunStateRepository(session),
            portal_key_repository=RiftPortalKeyRepository(session),
        ),
        character_sessions=app.state.character_sessions,
        rift_population_bindings=getattr(app.state, "rift_population_bindings", {}),
    )


__all__ = ["RiftEvents", "bind", "router"]
