from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from codex_platform.streams import StreamRouter
from loguru import logger

if TYPE_CHECKING:
    from fastapi import FastAPI

from src.backend.features.arena.repositories.session_store import ArenaSessionStore

router = StreamRouter()
_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("combat.session_ready", group="arena")
async def on_combat_session_ready(payload: dict[str, Any]) -> None:
    if _app is None or payload.get("source") != "arena":
        return
    arena_session_id = payload.get("arena_session_id")
    combat_id = payload.get("combat_id")
    if not arena_session_id or not combat_id:
        logger.warning("Arena combat ready ignored: missing ids payload={}", payload)
        return

    store = ArenaSessionStore(_app.state.redis)
    match = await store.get_match(str(arena_session_id))
    if match is None:
        logger.warning("Arena combat ready ignored: match_not_found arena_session_id={}", arena_session_id)
        return
    match.status = "ready"
    match.combat_id = str(combat_id)
    match.updated_at = _timestamp(payload)
    await store.update_match(match)
    logger.info("Arena match marked ready: arena_session_id={} combat_id={}", arena_session_id, combat_id)


@router.on("combat.session_failed", group="arena")
async def on_combat_session_failed(payload: dict[str, Any]) -> None:
    if _app is None or payload.get("source") != "arena":
        return
    arena_session_id = payload.get("arena_session_id")
    if not arena_session_id:
        return

    store = ArenaSessionStore(_app.state.redis)
    match = await store.get_match(str(arena_session_id))
    if match is None:
        logger.warning("Arena combat failure ignored: match_not_found arena_session_id={}", arena_session_id)
        return
    match.status = "failed"
    match.updated_at = _timestamp(payload)
    metadata = dict(match.metadata)
    if payload.get("error"):
        metadata["combat_error"] = str(payload["error"])
    match.metadata = metadata
    await store.update_match(match)
    logger.info("Arena match marked failed: arena_session_id={}", arena_session_id)


def _timestamp(payload: dict[str, Any]) -> float:
    import time

    value = payload.get("updated_at")
    if value is None:
        return time.time()
    try:
        return float(value)
    except (TypeError, ValueError):
        return time.time()


def _json_field(value: Any, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value if value is not None else default
