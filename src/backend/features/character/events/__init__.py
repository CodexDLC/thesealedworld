from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter

from src.backend.core.database.session import get_session_context
from src.backend.features.character.integrations import (
    CharacterCombatCommitmentIntegration,
    CharacterStateIntegrator,
    CharacterSystemIntegrator,
)
from src.backend.features.character.repositories import (
    CharacterAttributesRepository,
    CharacterRepository,
    SkillRepository,
)
from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.character.services import CharacterSessionPersistenceService, CharacterSkillService
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
    COMBAT_COMMITMENTS_REQUESTED = "character.combat_commitments_requested"
    COMBAT_COMMITMENTS_READY = "character.combat_commitments_ready"
    COMBAT_COMMITMENTS_FAILED = "character.combat_commitments_failed"
    GEAR_SCORE_RECALCULATE_REQUESTED = "character.gear_score_recalculate_requested"
    GEAR_SCORE_RECALCULATED = "character.gear_score_recalculated"
    GEAR_SCORE_RECALCULATE_FAILED = "character.gear_score_recalculate_failed"
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
                system_integrator=CharacterSystemIntegrator(
                    character_sessions=_app.state.character_sessions,
                    character_repo=CharacterRepository(session),
                    attributes_repo=CharacterAttributesRepository(session),
                    skill_repo=SkillRepository(session),
                ),
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


@router.on(CharacterEvents.COMBAT_COMMITMENTS_REQUESTED, group="character", reply=True)
async def on_combat_commitments_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Character combat commitments ignored: app_not_bound cid=%s", cid)
        return

    try:
        scope_id = str(payload.get("scope_id") or payload["session_id"])
        player_ids = [int(value) for value in _parse_json_list(payload.get("player_ids", []))]
        monster_ids = [str(value) for value in _parse_json_list(payload.get("monster_ids", []))]
        ttl = int(payload.get("ttl") or 300)
        result = await CharacterCombatCommitmentIntegration(
            character_sessions=_app.state.character_sessions,
            commitment_manager=_app.state.actor_commitments,
        ).prepare_commitments(
            scope_id=scope_id,
            player_ids=player_ids,
            monster_ids=monster_ids,
            ttl=ttl,
        )
        status = "partial" if result.failed_players or result.failed_monsters else "ok"
        ack: dict[str, Any] = {
            "status": status,
            "commitments": result.commitments,
            "failed_players": result.failed_players,
            "failed_monsters": result.failed_monsters,
        }
        await _app.state.events.publish(CharacterEvents.COMBAT_COMMITMENTS_READY, ack, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        log.exception("Character combat commitment request failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.COMBAT_COMMITMENTS_FAILED, {"request": payload, **ack})
        except Exception:
            log.exception("Character combat commitments failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Character combat commitments ack delivery failed: cid=%s", cid)


@router.on(CharacterEvents.GEAR_SCORE_RECALCULATE_REQUESTED, group="character", reply=True)
async def on_gear_score_recalculate_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        log.warning("Character gear score recalculation ignored: app_not_bound cid=%s", cid)
        return

    try:
        char_ids = [int(value) for value in _parse_json_list(payload.get("char_ids", []))]
        if not char_ids and payload.get("char_id") is not None:
            char_ids = [int(payload["char_id"])]
        calculator = CharacterGearScoreCalculator()
        sessions = await _app.state.character_sessions.get_sessions_batch(char_ids)
        gear_scores: dict[str, int] = {}
        failed: list[int] = []
        for char_id in char_ids:
            active_character = sessions.get(char_id)
            if not isinstance(active_character, dict):
                failed.append(char_id)
                continue
            gear_score = calculator.calculate_from_active_character(active_character)
            await _app.state.character_sessions.patch_fields(
                char_id,
                {"$.metrics.gear_score": gear_score},
            )
            gear_scores[str(char_id)] = gear_score
        ack = {"status": "partial" if failed else "ok", "gear_scores": gear_scores, "failed": failed}
        await _app.state.events.publish(CharacterEvents.GEAR_SCORE_RECALCULATED, ack, correlation_id=cid)
    except Exception as exc:  # noqa: BLE001
        log.exception("Character gear score recalculation failed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.GEAR_SCORE_RECALCULATE_FAILED, {"request": payload, **ack})
        except Exception:
            log.exception("Character gear score failure event delivery failed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            log.exception("Character gear score ack delivery failed: cid=%s", cid)


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
                state_integrator=CharacterStateIntegrator(
                    character_sessions=_app.state.character_sessions,
                    character_repo=CharacterRepository(session),
                    skill_repo=SkillRepository(session),
                ),
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
    parsed = _parse_json_list(raw)
    if not isinstance(parsed, list):
        raise ValueError("skill_keys must be a list")
    return [str(skill_key) for skill_key in parsed if skill_key]


def _parse_json_list(raw: Any) -> list[Any]:
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError("value must be a list")
    return parsed


__all__ = ["CharacterEvents", "bind", "router"]
