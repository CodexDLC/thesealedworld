from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from codex_platform.streams import StreamRouter
from loguru import logger

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


def with_log_context(
    handler: Callable[[dict[str, Any]], Awaitable[None]],
) -> Callable[[dict[str, Any]], Awaitable[None]]:
    async def wrapped(payload: dict[str, Any]) -> None:
        set_log_context(correlation_id=payload.get("correlation_id"))
        try:
            await handler(payload)
        finally:
            clear_log_context()

    return wrapped


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
    VITALS_RESTORE_REQUESTED = "character.vitals_restore_requested"
    VITALS_RESTORED = "character.vitals_restored"
    VITALS_RESTORE_FAILED = "character.vitals_restore_failed"


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on(CharacterEvents.ACTIVE_SESSION_SYNC_REQUESTED, group="character", reply=True)
@with_log_context
async def on_active_session_sync_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("CharacterActiveSessionSyncIgnored")
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
        logger.exception("CharacterActiveSessionSyncFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.ACTIVE_SESSION_SYNC_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("CharacterActiveSessionSyncFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("CharacterActiveSessionSyncAckDeliveryFailed")


@router.on(CharacterEvents.COMBAT_COMMITMENTS_REQUESTED, group="character", reply=True)
@with_log_context
async def on_combat_commitments_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("CharacterCombatCommitmentsIgnored")
        return

    try:
        player_ids = [int(value) for value in _parse_json_list(payload.get("player_ids", []))]
        monster_ids = [str(value) for value in _parse_json_list(payload.get("monster_ids", []))]
        ttl = int(payload.get("ttl") or 300)
        result = await CharacterCombatCommitmentIntegration(
            character_sessions=_app.state.character_sessions,
            commitment_manager=_app.state.actor_commitments,
        ).prepare_commitments(
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
        logger.exception("CharacterCombatCommitmentRequestFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.COMBAT_COMMITMENTS_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("CharacterCombatCommitmentsFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("CharacterCombatCommitmentsAckDeliveryFailed")


@router.on(CharacterEvents.VITALS_RESTORE_REQUESTED, group="character", reply=True)
@with_log_context
async def on_vitals_restore_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("CharacterVitalsRestoreIgnored")
        return

    try:
        char_id = int(payload["char_id"])
        vitals = await _app.state.character_sessions.restore_vitals_to_max(char_id)
        ack: dict[str, Any] = {"status": "ok", "char_id": char_id, "vitals": vitals}
        await _app.state.events.publish(
            CharacterEvents.VITALS_RESTORED,
            {"char_id": char_id, "reason": payload.get("reason") or "restore_requested"},
            correlation_id=cid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("CharacterVitalsRestoreFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.VITALS_RESTORE_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("CharacterVitalsRestoreFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("CharacterVitalsRestoreAckDeliveryFailed")


@router.on(CharacterEvents.GEAR_SCORE_RECALCULATE_REQUESTED, group="character", reply=True)
@with_log_context
async def on_gear_score_recalculate_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("CharacterGearScoreRecalculationIgnored")
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
        logger.exception("CharacterGearScoreRecalculationFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.GEAR_SCORE_RECALCULATE_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("CharacterGearScoreFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("CharacterGearScoreAckDeliveryFailed")


@router.on(CharacterEvents.SKILLS_UNLOCK_REQUESTED, group="character", reply=True)
@with_log_context
async def on_skills_unlock_requested(payload: dict[str, Any]) -> None:
    cid = payload.get("correlation_id")
    if _app is None:
        logger.warning("CharacterSkillsUnlockIgnored")
        return

    try:
        char_id = int(payload["char_id"])
        skill_keys = _parse_skill_keys(payload)
        progress_state = SkillProgressState(payload.get("progress_state") or SkillProgressState.PLUS.value)
        initial_xp = _parse_initial_xp(payload)
        async with get_session_context() as session:
            service = CharacterSkillService(
                state_integrator=CharacterStateIntegrator(
                    character_sessions=_app.state.character_sessions,
                    character_repo=CharacterRepository(session),
                    skill_repo=SkillRepository(session),
                ),
            )
            unlocked = await service.unlock_skills(
                char_id,
                skill_keys,
                progress_state=progress_state,
                initial_xp=initial_xp,
            )

        ack: dict[str, Any] = {"status": "ok", "char_id": char_id, "skill_keys": unlocked}
        await _app.state.events.publish(
            CharacterEvents.SKILLS_UNLOCKED,
            {"char_id": char_id, "skill_keys": unlocked},
            correlation_id=cid,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("CharacterSkillsUnlockFailed")
        ack = {"status": "error", "error": f"{exc.__class__.__name__}: {exc}"}
        try:
            await _app.state.events.publish(CharacterEvents.SKILLS_UNLOCK_FAILED, {"request": payload, **ack})
        except Exception:
            logger.exception("CharacterSkillsUnlockFailureEventDeliveryFailed")

    if cid:
        try:
            await _app.state.events.publish_reply(cid, ack, ttl=30)
        except Exception:
            logger.exception("CharacterSkillsUnlockAckDeliveryFailed")


def _parse_skill_keys(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("skill_keys", "[]")
    parsed = _parse_json_list(raw)
    if not isinstance(parsed, list):
        raise ValueError("skill_keys must be a list")
    return [str(skill_key) for skill_key in parsed if skill_key]


def _parse_initial_xp(payload: dict[str, Any]) -> float:
    raw = payload.get("initial_xp", payload.get("initial_skill_xp", 0.0))
    try:
        return min(1.0, max(0.0, float(raw or 0.0)))
    except (TypeError, ValueError):
        raise ValueError("initial_xp must be a number") from None


def _parse_json_list(raw: Any) -> list[Any]:
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError("value must be a list")
    return parsed


__all__ = ["CharacterEvents", "bind", "router"]
