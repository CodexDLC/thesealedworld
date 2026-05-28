from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from codex_core.common.log_context import clear_log_context, set_log_context
from codex_platform.streams import StreamRouter
from loguru import logger

if TYPE_CHECKING:
    from fastapi import FastAPI

    from src.backend.infrastructure.arena.schemas.session import ArenaQueueSessionSchema, ArenaRuntimeSessionSchema

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO
from src.backend.infrastructure.arena.managers import ArenaSessionManager

router = StreamRouter()
_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    global _app
    _app = app


@router.on("combat.session_ready", group="arena")
async def on_combat_session_ready(payload: dict[str, Any]) -> None:
    set_log_context(correlation_id=payload.get("correlation_id"))
    try:
        if _app is None or payload.get("source") != "arena":
            return
        arena_session_id = payload.get("arena_session_id")
        combat_id = payload.get("combat_id")
        if not arena_session_id or not combat_id:
            logger.bind(payload=payload).warning("ArenaCombatReadyIgnored")
            return

        store: ArenaSessionManager[
            ArenaQueueSessionSchema,
            ArenaCombatRequestDTO,
            ArenaRuntimeSessionSchema,
        ] = ArenaSessionManager(_app.state.redis, combat_schema=ArenaCombatRequestDTO)
        match = await store.get_match(str(arena_session_id))
        if match is None:
            logger.bind(arena_session_id=arena_session_id).warning("ArenaCombatReadyMatchMissing")
            return
        match.status = "ready"
        match.combat_id = str(combat_id)
        match.updated_at = _timestamp(payload)
        await store.update_match(match)
        logger.bind(arena_session_id=arena_session_id, combat_id=combat_id).info("ArenaMatchMarkedReady")
    finally:
        clear_log_context()


@router.on("combat.session_failed", group="arena")
async def on_combat_session_failed(payload: dict[str, Any]) -> None:
    set_log_context(correlation_id=payload.get("correlation_id"))
    try:
        if _app is None or payload.get("source") != "arena":
            return
        arena_session_id = payload.get("arena_session_id")
        if not arena_session_id:
            return

        store: ArenaSessionManager[
            ArenaQueueSessionSchema,
            ArenaCombatRequestDTO,
            ArenaRuntimeSessionSchema,
        ] = ArenaSessionManager(_app.state.redis, combat_schema=ArenaCombatRequestDTO)
        match = await store.get_match(str(arena_session_id))
        if match is None:
            logger.bind(arena_session_id=arena_session_id).warning("ArenaCombatFailureMatchMissing")
            return
        match.status = "failed"
        match.updated_at = _timestamp(payload)
        metadata = dict(match.metadata)
        if payload.get("error"):
            metadata["combat_error"] = str(payload["error"])
        match.metadata = metadata
        await store.update_match(match)
        logger.bind(arena_session_id=arena_session_id).info("ArenaMatchMarkedFailed")
    finally:
        clear_log_context()


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
