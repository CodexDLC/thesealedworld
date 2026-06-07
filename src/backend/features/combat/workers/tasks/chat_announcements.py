from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any

from loguru import logger as log

from src.backend.infrastructure.combat.managers import CombatAnnouncementManager
from src.backend.realtime.integrations.notice_publisher import PlayerNoticePublisher, RawStreamNoticeProducer


async def publish_combat_start_announcement(ctx: dict[str, Any], data_service: Any, session_id: str) -> None:
    redis = ctx.get("redis_client_internal")
    if redis is None:
        log.bind(reason="no_redis", kind="start", session_id=session_id).warning("CombatAnnouncementSkipped")
        return
    if not await _claim_once(CombatAnnouncementManager(redis), session_id, "start"):
        return

    meta = await data_service.get_meta(session_id)
    meta = meta if isinstance(meta, dict) else {}
    if str(meta.get("active", "1")) in {"0", "false", "False"}:
        return

    teams = _decode_json(meta.get("teams"), default={})
    actor_ids = [str(actor_id) for actor_id in data_service.actor_ids_from_meta(meta)]
    actors = await data_service.get_actors_batch(session_id, actor_ids)
    recipients = _player_recipients(actor_ids, actors)
    if not recipients:
        return

    team_summaries = _team_summaries(teams, actors, final=False)
    if not team_summaries:
        return

    participants = " против ".join(team_summaries)
    await _publish_system_notice(
        redis,
        recipients=recipients,
        kind="start",
        publish=lambda publisher, recipient_ids: publisher.combat_started(
            recipient_ids,
            time_text=_time_text(meta.get("started_at") or meta.get("start_time")),
            participants=participants,
        ),
    )


async def publish_combat_final_announcement(ctx: dict[str, Any], finalization: dict[str, Any]) -> None:
    redis = ctx.get("redis_client_internal")
    session_id = str(finalization.get("combat_id") or "")
    if redis is None or not session_id:
        log.bind(reason="no_redis_or_session", kind="final", session_id=session_id).warning("CombatAnnouncementSkipped")
        return
    if not await _claim_once(CombatAnnouncementManager(redis), session_id, "final"):
        return

    recipients = [str(char_id) for char_id in finalization.get("participant_char_ids", []) if char_id is not None]
    if not recipients:
        return

    raw_teams = finalization.get("teams")
    teams = raw_teams if isinstance(raw_teams, dict) else {}

    raw_actors = finalization.get("actors")
    actors = raw_actors if isinstance(raw_actors, dict) else {}

    raw_report = finalization.get("report")
    report = raw_report if isinstance(raw_report, dict) else {}

    winner = str(finalization.get("winner_team") or "")
    last_turn = report.get("last_turn")

    if winner == "draw":
        outcome = _with_turn("ничья", last_turn)
    else:
        winner_summary = _team_summary(winner, teams.get(winner), actors, final=True)
        outcome = _with_turn(f"победила {winner_summary}", last_turn)

    team_summaries = _team_summaries(teams, actors, final=True)
    participants = "; ".join(team_summaries) if team_summaries else "данные участников уточняются"

    await _publish_system_notice(
        redis,
        recipients=recipients,
        kind="final",
        publish=lambda publisher, recipient_ids: publisher.combat_finished(
            recipient_ids,
            time_text=_time_text(finalization.get("finished_at")),
            outcome=outcome,
            participants=participants,
        ),
    )


async def _claim_once(announcements: CombatAnnouncementManager, session_id: str, kind: str) -> bool:
    try:
        return await announcements.claim_once(session_id, kind)
    except Exception:
        log.bind(session_id=session_id, kind=kind).exception("CombatAnnouncementClaimFailed")
        return False


async def _publish_system_notice(
    redis: Any,
    *,
    recipients: list[str],
    kind: str,
    publish: Any,
) -> None:
    recipient_ids = [int(recipient) for recipient in recipients if str(recipient).isdigit()]
    if not recipient_ids:
        return
    try:
        await publish(PlayerNoticePublisher(RawStreamNoticeProducer(redis)), recipient_ids)
    except Exception:
        log.bind(recipients=recipients, kind=kind).exception("CombatAnnouncementPublishFailed")


def _team_summaries(teams: Any, actors: dict[str, Any], *, final: bool) -> list[str]:
    if not isinstance(teams, dict):
        return []
    return [
        summary
        for team, members in teams.items()
        for summary in [_team_summary(str(team), members, actors, final=final)]
        if summary
    ]


def _team_summary(team: str, members: Any, actors: dict[str, Any], *, final: bool) -> str:
    member_ids = [str(member) for member in members] if isinstance(members, list) else []
    labels = [_actor_label(actor_id, actors.get(actor_id), final=final) for actor_id in member_ids]
    labels = [label for label in labels if label]
    if not labels:
        return _team_label(team)
    return f"{_team_label(team)}: {', '.join(labels)}"


def _actor_label(actor_id: str, actor: Any, *, final: bool) -> str:
    if not isinstance(actor, dict):
        return actor_id
    raw_meta = actor.get("meta")
    meta = raw_meta if isinstance(raw_meta, dict) else {}
    name = str(actor.get("name") or meta.get("name") or actor_id)
    vitals = actor.get("vitals_final") if final and isinstance(actor.get("vitals_final"), dict) else meta
    hp = _optional_int(vitals.get("hp") if isinstance(vitals, dict) else None)
    max_hp = _optional_int(vitals.get("max_hp") if isinstance(vitals, dict) else None)
    if hp is None or max_hp is None:
        return name
    return f"{name}[{hp}/{max_hp}]"


def _player_recipients(actor_ids: list[str], actors: dict[str, Any]) -> list[str]:
    recipients: list[str] = []
    for actor_id in actor_ids:
        actor = actors.get(actor_id)
        if not isinstance(actor, dict):
            continue
        raw_meta = actor.get("meta")
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        if meta.get("type") == "monster" or meta.get("is_ai") is True:
            continue
        if actor_id.isdigit():
            recipients.append(actor_id)
    return list(dict.fromkeys(recipients))


def _time_text(value: Any) -> str:
    timestamp = _optional_int(value)
    if timestamp is None:
        timestamp = int(time.time())
    return datetime.fromtimestamp(timestamp, tz=UTC).strftime("%H:%M")


def _with_turn(outcome: str, last_turn: Any) -> str:
    turn = _optional_int(last_turn)
    if turn is None:
        return outcome
    return f"{outcome} на ходу {turn}"


def _team_label(team: str) -> str:
    suffix = team.removeprefix("team_")
    return f"Команда {suffix}" if suffix else "Команда"


def _decode_json(value: Any, *, default: Any) -> Any:
    if isinstance(value, dict | list):
        return value
    if value in (None, ""):
        return default
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
