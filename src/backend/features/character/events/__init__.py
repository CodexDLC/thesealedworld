from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_session_context
from src.backend.features.character.services import CharacterSessionPersistenceService, CharacterSkillService
from src.backend.infrastructure.actor_state.repositories import SkillRepository
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from fastapi import FastAPI

router = StreamRouter()
_app: FastAPI | None = None
log = logging.getLogger(__name__)


class CharacterEvents:
    ACTIVE_SESSION_SYNC_REQUESTED = "character.active_session_sync_requested"
    ACTIVE_SESSION_SYNCED = "character.active_session_synced"
    ACTIVE_SESSION_SYNC_FAILED = "character.active_session_sync_failed"
    SKILLS_UNLOCK_REQUESTED = "character.skills_unlock_requested"
    SKILLS_UNLOCKED = "character.skills_unlocked"
    SKILLS_UNLOCK_FAILED = "character.skills_unlock_failed"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(CharacterEvents.ACTIVE_SESSION_SYNC_REQUESTED, group="character", reply=True)
async def on_active_session_sync_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Character active session sync ignored: app_not_bound cid=%s", cid)
        return

    try:
        char_id = int(payload["char_id"])
        async with get_session_context() as session:
            service = CharacterSessionPersistenceService(
                db_session=session,
                character_sessions=_app.state.character_sessions,
            )
            synced = await service.sync_active_session_to_db(char_id)

        ack: dict[str, Any] = {"status": "ok", **synced}
        await _app.state.events.publish(CharacterEvents.ACTIVE_SESSION_SYNCED, synced, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        log.exception("Character active session sync failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.ACTIVE_SESSION_SYNC_FAILED, {"request": payload, **ack})
        except Exception:
            log.exception("Character active session sync failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Character active session sync ack delivery failed: cid=%s", cid)


@router.on(CharacterEvents.SKILLS_UNLOCK_REQUESTED, group="character", reply=True)
async def on_skills_unlock_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Character skills unlock ignored: app_not_bound cid=%s", cid)
        return

    try:
        char_id = int(payload["char_id"])
        skill_keys = _parse_skill_keys(payload)
        progress_state = SkillProgressState(payload.get("progress_state") or SkillProgressState.PLUS.value)
        async with get_session_context() as session:
            service = CharacterSkillService(
                skill_repo=SkillRepository(session),
                character_sessions=_app.state.character_sessions,
            )
            unlocked = await service.unlock_skills(char_id, skill_keys, progress_state=progress_state)

        ack: dict[str, Any] = {"status": "ok", "char_id": char_id, "skill_keys": unlocked}
        await _app.state.events.publish(
            CharacterEvents.SKILLS_UNLOCKED,
            {"char_id": char_id, "skill_keys": unlocked},
            correlation_id=cid,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Character skills unlock failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.SKILLS_UNLOCK_FAILED, {"request": payload, **ack})
        except Exception:
            log.exception("Character skills unlock failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Character skills unlock ack delivery failed: cid=%s", cid)


def _parse_skill_keys(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("skill_keys", "[]")
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(parsed, list):
        raise ValueError("skill_keys must be a list")
    return [str(skill_key) for skill_key in parsed if skill_key]


__all__ = ["CharacterEvents", "bind", "router"]
