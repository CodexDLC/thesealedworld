from __future__ import annotations

import copy
from typing import Any

from loguru import logger

from src.backend.realtime.integrations.notice_publisher import (
    PlayerNoticePublisher,
    RawStreamNoticeProducer,
    RefreshTargets,
)
from src.shared.infrastructure.log_task_wrapper import logged_task


def _build_notice_publisher(ctx: dict[str, Any]) -> PlayerNoticePublisher | None:
    events = ctx.get("events")
    if events is not None:
        return PlayerNoticePublisher(events)
    redis = ctx.get("redis_client_internal")
    if redis is not None:
        return PlayerNoticePublisher(RawStreamNoticeProducer(redis))
    return None


@logged_task
async def online_vitals_regen_task(ctx: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = int(payload.get("limit") or 100)
    now = payload.get("now")
    managers = ctx["redis_managers"]
    sessions = managers.character_sessions
    notice_publisher = _build_notice_publisher(ctx)

    candidate_ids = await sessions.scan_vitals_regen_candidates(limit=limit)
    processed: list[int] = []
    refreshed: list[int] = []
    for char_id in candidate_ids:
        before = copy.deepcopy(await sessions.get_section(char_id, "vitals"))
        updated = (
            await sessions.apply_vitals_regen(char_id)
            if now is None
            else await sessions.apply_vitals_regen(char_id, now=now)
        )
        if updated != before:
            processed.append(char_id)
            refreshed.append(char_id)
            if notice_publisher is not None:
                await notice_publisher.request_refresh(
                    char_id,
                    target=RefreshTargets.STATUS,
                    reason="vitals_regenerated",
                    domain="system",
                )

    logger.bind(candidate_count=len(candidate_ids), processed_count=len(processed)).info("OnlineVitalsRegenCompleted")
    return {
        "status": "ok",
        "candidate_char_ids": candidate_ids,
        "processed_char_ids": processed,
        "refreshed_char_ids": refreshed,
    }
