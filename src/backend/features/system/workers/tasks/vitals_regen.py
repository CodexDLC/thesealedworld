from __future__ import annotations

import asyncio
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


def _chunked(values: list[int], size: int) -> list[list[int]]:
    if not values:
        return []
    size = max(1, size)
    return [values[index : index + size] for index in range(0, len(values), size)]


@logged_task
async def online_vitals_regen_task(ctx: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = int(payload.get("limit") or 100)
    batch_size = int(payload.get("batch_size") or limit or 100)
    batch_pause_ms = int(payload.get("batch_pause_ms") or 0)
    managers = ctx["redis_managers"]
    sessions = managers.character_sessions
    notice_publisher = _build_notice_publisher(ctx)

    candidate_ids = await sessions.scan_vitals_regen_candidates(limit=limit)
    notified: list[int] = []
    batches = _chunked(candidate_ids, batch_size)
    if notice_publisher is not None:
        for index, batch in enumerate(batches):
            await notice_publisher.request_refresh_many(
                batch,
                target=RefreshTargets.STATUS,
                reason="vitals_refresh_requested",
                domain="system",
            )
            notified.extend(batch)
            if batch_pause_ms > 0 and index < len(batches) - 1:
                await asyncio.sleep(batch_pause_ms / 1000)

    logger.bind(
        candidate_count=len(candidate_ids),
        notified_count=len(notified),
        batch_count=len(batches),
    ).info("OnlineVitalsRefreshRequested")
    return {
        "status": "ok",
        "candidate_char_ids": candidate_ids,
        "notified_char_ids": notified,
        "batch_count": len(batches),
    }
