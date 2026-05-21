from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from src.backend.core.database.session import get_session_context
from src.backend.features.exploration.repositories.knowledge import CharacterLocationKnowledgeRepository
from src.backend.features.exploration.services.knowledge_runtime import ExplorationKnowledgeRuntimeManager
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def flush_exploration_knowledge_task(ctx: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    char_id = int(payload["char_id"])
    limit = int(payload.get("limit") or 100)
    redis_managers = ctx["redis_managers"]
    runtime = ExplorationKnowledgeRuntimeManager(redis_managers.redis)
    loc_ids = await runtime.dirty_loc_ids(char_id, limit=limit)
    if not loc_ids:
        logger.bind(char_id=char_id).debug("ExplorationKnowledgeFlushSkipped")
        return {"status": "skipped", "reason": "clean", "char_id": char_id}

    rows: list[dict[str, Any]] = []
    cleared: list[str] = []
    for loc_id in loc_ids:
        document = await runtime.get(char_id, loc_id)
        if document is None:
            cleared.append(loc_id)
            continue
        rows.append(_row_from_runtime(char_id, loc_id, document))
        cleared.append(loc_id)

    if rows:
        async with get_session_context() as session:
            repository = CharacterLocationKnowledgeRepository(session)
            await repository.upsert_rows(rows)

    await runtime.clear_dirty(char_id, cleared)
    logger.bind(char_id=char_id, row_count=len(rows), cleared_count=len(cleared)).info(
        "ExplorationKnowledgeFlushCompleted"
    )
    return {"status": "ok", "char_id": char_id, "rows": len(rows), "cleared": len(cleared)}


def _row_from_runtime(char_id: int, loc_id: str, document: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "character_id": char_id,
        "loc_id": loc_id,
        "movement_xp_spent": _number(document.get("movement_xp_spent")),
        "scouting_xp_spent": _number(document.get("scouting_xp_spent")),
        "hunting_xp_spent": _number(document.get("hunting_xp_spent")),
        "movement_xp_cap": _number(document.get("movement_xp_cap")),
        "scouting_xp_cap": _number(document.get("scouting_xp_cap")),
        "hunting_xp_cap": _number(document.get("hunting_xp_cap")),
        "discovered_at": _datetime(document.get("discovered_at")) or now,
        "last_visited_at": _datetime(document.get("last_visited_at")) or now,
        "metadata": _dict(document.get("metadata")),
        "context": _dict(document.get("context")),
        "source_context": _dict(document.get("source_context")),
        "schema_version": int(_number(document.get("schema_version")) or 1),
        "revision": int(_number(document.get("revision"))),
    }


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
