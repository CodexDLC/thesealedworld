from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/internal/exploration", tags=["exploration-internal"])


def _get_client(redis: Any) -> Any:
    if hasattr(redis, "redis_client"):
        return redis.redis_client
    return redis.pipeline.client


@router.get("/sessions")
async def list_encounter_sessions(request: Request) -> list[dict]:
    redis = request.app.state.redis
    client = _get_client(redis)

    keys: list[Any] = []
    cursor = 0
    while True:
        cursor, batch = await client.scan(cursor, match="game:encounter:*", count=100)
        keys.extend(batch)
        if cursor == 0:
            break

    results = []
    for key in keys:
        try:
            raw = await redis.json_module.get(key, "$")
            doc = raw[0] if isinstance(raw, list) and raw else None
            if not isinstance(doc, dict):
                continue
            payload = doc.get("payload") or {}
            results.append(
                {
                    "encounter_id": doc.get("encounter_id", "—"),
                    "char_id": str(doc.get("char_id", "—")),
                    "status": doc.get("status", "—"),
                    "type": payload.get("type", "—"),
                    "title": payload.get("title", "—"),
                }
            )
        except Exception:
            continue

    return results
