import logging
from typing import Any

from codex_platform.streams import StreamRouter
from fastapi import FastAPI

from src.backend.features.actor_state.dto.snapshot import SnapshotsRequest
from src.backend.features.actor_state.services.actor_state_service import ActorStateService

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("actor_state.snapshots_requested", group="actor_state", reply=True)
async def on_snapshots_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if not cid or _app is None:
        log.warning(
            "ActorState snapshots request ignored: missing_correlation_or_app cid=%s app_bound=%s",
            cid,
            _app is not None,
        )
        return

    try:
        request = SnapshotsRequest.model_validate(payload)
        log.info(
            "ActorState snapshots request received: session_id=%s players=%s monsters=%s",
            request.session_id,
            len(request.player_ids),
            len(request.monster_ids),
        )
        service = ActorStateService(_app.state.actor_snapshots, _app.state.redis)
        result = await service.prepare_snapshots(
            session_id=request.session_id,
            player_ids=request.player_ids,
            monster_ids=request.monster_ids,
            ttl=request.ttl,
            include=request.include,
            exclude=request.exclude,
        )
        if result.failed_players or result.failed_monsters:
            log.warning(
                "ActorState snapshots partially prepared: session_id=%s failed_players=%s failed_monsters=%s",
                request.session_id,
                len(result.failed_players),
                len(result.failed_monsters),
            )
            ack: dict[str, Any] = {
                "status": "partial",
                "failed_players": result.failed_players,
                "failed_monsters": result.failed_monsters,
                "snapshot_keys": result.snapshot_keys,
            }
        else:
            log.info(
                "ActorState snapshots prepared: session_id=%s players=%s monsters=%s",
                request.session_id,
                result.counts.get("players", 0),
                result.counts.get("monsters", 0),
            )
            ack = {
                "status": "ok",
                "players": result.counts.get("players", 0),
                "monsters": result.counts.get("monsters", 0),
                "failed": [],
                "snapshot_keys": result.snapshot_keys,
            }
    except Exception as exc:  # noqa: BLE001
        log.exception("ActorState snapshots request failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}

    try:
        await _app.state.events.publish_reply(cid, ack, ttl=30)
    except Exception:
        log.exception("ActorState snapshots ack delivery failed: cid=%s", cid)
