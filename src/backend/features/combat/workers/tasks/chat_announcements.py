from __future__ import annotations

import json
from typing import Any

from codex_platform.streams.codec import encode_stream_payload
from loguru import logger as log

from src.backend.config.settings import settings

_ANNOUNCEMENT_TTL_SECONDS = 86400


async def publish_combat_start_announcement(ctx: dict[str, Any], data_service: Any, session_id: str) -> None:
    redis = ctx.get("redis_client_internal")
    if redis is None:
        log.bind(reason="no_redis", kind="start", session_id=session_id).warning("CombatAnnouncementSkipped")
        return
    if not await _claim_once(redis, session_id, "start"):
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

    content = "Бой начался: " + " против ".join(team_summaries) + "."
    await _publish_announcement(
        redis,
        session_id=session_id,
        recipients=recipients,
        kind="start",
        label="БОЙ НАЧАЛСЯ",
        content=content,
        result={"teams": teams},
    )


async def publish_combat_final_announcement(ctx: dict[str, Any], finalization: dict[str, Any]) -> None:
    redis = ctx.get("redis_client_internal")
    session_id = str(finalization.get("combat_id") or "")
    if redis is None or not session_id:
        log.bind(reason="no_redis_or_session", kind="final", session_id=session_id).warning("CombatAnnouncementSkipped")
        return
    if not await _claim_once(redis, session_id, "final"):
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

    turn_text = f" на ходу {last_turn}" if last_turn is not None else ""
    if winner == "draw":
        lead = f"Бой завершен{turn_text}. Ничья."
    else:
        winner_summary = _team_summary(winner, teams.get(winner), actors, final=True)
        lead = f"Бой завершен{turn_text}. Победила {winner_summary}."

    team_summaries = _team_summaries(teams, actors, final=True)
    content = lead
    if team_summaries:
        content += " Участники: " + "; ".join(team_summaries) + "."

    await _publish_announcement(
        redis,
        session_id=session_id,
        recipients=recipients,
        kind="final",
        label="БОЙ ЗАВЕРШЕН",
        content=content,
        result={"teams": teams, "actors": actors, "winner_team": winner, "last_turn": last_turn},
        global_turn=last_turn,
    )


async def _claim_once(redis: Any, session_id: str, kind: str) -> bool:
    key = f"combat:announcement:{session_id}:{kind}"
    try:
        return bool(await redis.set(key, "1", nx=True, ex=_ANNOUNCEMENT_TTL_SECONDS))
    except Exception:
        log.bind(session_id=session_id, kind=kind).exception("CombatAnnouncementClaimFailed")
        return False


async def _publish_announcement(
    redis: Any,
    *,
    session_id: str,
    recipients: list[str],
    kind: str,
    label: str,
    content: str,
    result: dict[str, Any],
    global_turn: Any = None,
) -> None:
    payload = {
        "scope_id": session_id,
        "recipients": recipients,
        "content": content,
        "template": {"text": content},
        "variables": {},
        "result": result,
        "presentation": {
            "render": "combat_log",
            "variant": "combat_announcement",
            "separator": {
                "label": label,
                "key": f"combat:{session_id}:announcement:{kind}",
            },
        },
        "meta": {
            "combat_session_id": session_id,
            "announcement": kind,
            "global_turn": global_turn,
        },
    }
    try:
        await redis.xadd(
            settings.game_stream_name,
            encode_stream_payload({"type": "chat.combat_log_message", **payload}),
            maxlen=settings.game_stream_maxlen,
            approximate=True,
        )
    except Exception:
        log.bind(session_id=session_id, kind=kind).exception("CombatAnnouncementPublishFailed")


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
