from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/internal/scenario", tags=["scenario-internal"])


def _get_client(redis: Any) -> Any:
    if hasattr(redis, "redis_client"):
        return redis.redis_client
    return redis.pipeline.client


@router.get("/sessions")
async def list_scenario_sessions(request: Request) -> list[dict]:
    redis = request.app.state.redis
    client = _get_client(redis)

    keys: list[Any] = []
    cursor = 0
    while True:
        cursor, batch = await client.scan(cursor, match="game:ac:*:scenario", count=100)
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
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.split(":")
            char_id = parts[2] if len(parts) >= 4 else "?"
            results.append(
                {
                    "char_id": char_id,
                    "session_id": doc.get("scenario_session_id", "—"),
                    "quest_key": doc.get("quest_key", "—"),
                    "current_node": doc.get("current_node_key", "—"),
                    "step": f"{doc.get('step_counter', 0)}/{doc.get('total_steps', '?')}",
                    "updated_at": doc.get("updated_at", "—"),
                }
            )
        except Exception:
            continue

    return results
