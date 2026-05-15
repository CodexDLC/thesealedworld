from typing import Any

from loguru import logger as log

from src.backend.core.database import get_session_context
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.combat.runtime.services.durability_policy import CombatDurabilityPolicy
from src.backend.features.combat.runtime.services.experience_finalizer import CombatExperienceFinalizer
from src.backend.features.combat.runtime.services.finalization_builder import CombatFinalizationBuilder
from src.backend.features.combat.workers.tasks.chat_announcements import publish_combat_final_announcement
from src.backend.features.expedition import ExpeditionService
from src.backend.features.inventory.events.publisher import InventoryEvents
from src.shared.enums import CoreDomain


async def victory_finalizer_task(ctx: dict, data: dict) -> None:
    """
    Финализатор боя (Victory Finalizer).

    Выполняется после определения победителя.
    Отвечает за завершение боя и начисление наград.

    Args:
        ctx: Контекст ARQ.
        data: Данные финализации (session_id, winner).
    """
    session_id = data.get("session_id", "unknown")
    winner = data.get("winner", "unknown")

    log.info(
        "VictoryFinalizer | session_id={session_id} winner={winner} status=processing",
        session_id=session_id,
        winner=winner,
    )

    data_service: CombatDataService | None = ctx.get("combat_data_service")
    if not data_service:
        log.error("VictoryFinalizer | CombatDataService not found in context")
        return

    try:
        # 1. Устанавливаем статус победы в Redis
        await data_service.set_battle_winner(session_id, winner)

        # 2. Commit final combat vitals back into the active character session.
        await _commit_player_vitals_to_active_sessions(ctx, data_service, session_id)

        # 3. Convert flat runtime xp_buffer counters into character progression rewards.
        async with get_session_context() as session:
            expedition_service = ExpeditionService(
                session=session,
                character_sessions=ctx.get("character_sessions"),
                expedition_manager=ctx.get("expeditions"),
                world_store=ctx.get("world_locations"),
            )
            progression_results = await CombatExperienceFinalizer().finalize(
                data_service,
                session_id,
                winner,
                character_sessions=ctx.get("character_sessions"),
                progression_recorder=expedition_service,
            )

        # 4. Freeze final combat facts before runtime cleanup can remove actor/session keys.
        finalization = await CombatFinalizationBuilder().build(
            data_service,
            session_id,
            winner,
            progression_results=progression_results,
        )
        save_finalization = getattr(data_service, "save_finalization", None)
        if save_finalization is not None:
            await save_finalization(
                session_id,
                finalization,
                char_ids=finalization.get("participant_char_ids", []),
                ttl=86400,
            )
            await _apply_durability_consequences(ctx, finalization)
            await _attach_finalization_to_active_sessions(ctx, session_id, finalization)
            await publish_combat_final_announcement(ctx, finalization)
            await _enqueue_finalization_persist(ctx, session_id)

        log.info(f"VictoryFinalizer | Battle {session_id} finalized successfully")

    except Exception as e:  # noqa: BLE001
        log.exception(f"VictoryFinalizer | Failed to finalize battle {session_id}: {e}")


async def _enqueue_finalization_persist(ctx: dict, session_id: str) -> None:
    queue = ctx.get("redis")
    if queue is None:
        return
    await queue.enqueue_job("combat_finalization_persist_task", {"combat_id": session_id})


async def _apply_durability_consequences(ctx: dict, finalization: dict[str, Any]) -> None:
    events = ctx.get("events")
    request = getattr(events, "request", None)
    if request is None:
        return

    for durability_request in CombatDurabilityPolicy().resolve(finalization):
        payload = durability_request.as_payload()
        try:
            response = await request(
                InventoryEvents.DURABILITY_DAMAGE_REQUESTED,
                payload,
                timeout=30.0,
                correlation_id=durability_request.idempotency_key,
            )
            if isinstance(response, dict) and response.get("status") == "error":
                log.warning(
                    "VictoryFinalizer | durability damage failed char_id={} combat_id={} error={}",
                    durability_request.char_id,
                    durability_request.combat_id,
                    response.get("error"),
                )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "VictoryFinalizer | durability damage request failed char_id={} combat_id={} error={}",
                durability_request.char_id,
                durability_request.combat_id,
                exc,
            )


async def _attach_finalization_to_active_sessions(ctx: dict, session_id: str, finalization: dict[str, Any]) -> None:
    character_sessions = ctx.get("character_sessions")
    if character_sessions is None:
        return

    char_ids = [int(char_id) for char_id in finalization.get("participant_char_ids", []) if _int_or_none(char_id)]
    dead_char_ids = {
        int(actor.get("char_id"))
        for actor in (finalization.get("actors") or {}).values()
        if isinstance(actor, dict) and actor.get("char_id") is not None and actor.get("is_dead") is True
    }
    location_id = (
        (finalization.get("meta") or {}).get("location_id") if isinstance(finalization.get("meta"), dict) else None
    )
    death_marked: set[int] = set()
    if dead_char_ids:
        async with get_session_context() as session:
            expedition_service = ExpeditionService(
                session=session,
                character_sessions=character_sessions,
                expedition_manager=ctx.get("expeditions"),
                world_store=ctx.get("world_locations"),
            )
            for char_id in dead_char_ids:
                if await expedition_service.mark_death_pending(
                    char_id=char_id,
                    combat_id=session_id,
                    location_id=str(location_id) if location_id else None,
                ):
                    death_marked.add(char_id)

    for char_id in char_ids:
        if char_id in death_marked:
            continue
        await character_sessions.patch_fields(
            char_id,
            {
                "$.sessions.combat_id": None,
                "$.sessions.combat_finalization_id": str(session_id),
                "$.state": CoreDomain.COMBAT_RESULT.value,
            },
        )
        await character_sessions.mark_dirty(
            char_id,
            reason="combat_finalization_attached",
            paths=["$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.state"],
        )


async def _commit_player_vitals_to_active_sessions(ctx: dict, data_service: CombatDataService, session_id: str) -> None:
    character_sessions = ctx.get("character_sessions")
    if character_sessions is None:
        log.warning("VictoryFinalizer | active character sessions unavailable session_id={}", session_id)
        return

    meta = await data_service.get_meta(session_id)
    if not isinstance(meta, dict):
        log.warning("VictoryFinalizer | combat meta unavailable for vitals commit session_id={}", session_id)
        return

    actor_ids = [actor_id for actor_id in data_service.actor_ids_from_meta(meta) if str(actor_id).isdigit()]
    if not actor_ids:
        return

    actors = await data_service.get_actors_batch(session_id, actor_ids)
    for actor_id, actor in actors.items():
        actor_meta = actor.get("meta") if isinstance(actor, dict) else None
        if not isinstance(actor_meta, dict):
            continue

        char_id = int(actor_id)
        await _update_vital_if_present(
            character_sessions, char_id, "hp", actor_meta.get("hp"), actor_meta.get("max_hp")
        )
        await _update_vital_if_present(
            character_sessions,
            char_id,
            "energy",
            actor_meta.get("en"),
            actor_meta.get("max_en"),
        )
        await _update_vital_if_present(
            character_sessions,
            char_id,
            "stamina",
            actor_meta.get("stamina"),
            actor_meta.get("max_stamina"),
        )


async def _update_vital_if_present(
    character_sessions: Any,
    char_id: int,
    vital: str,
    cur: Any,
    max_value: Any,
) -> None:
    if cur is None and max_value is None:
        return
    await character_sessions.update_vital(char_id, vital, cur=_int_or_none(cur), max=_int_or_none(max_value))


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
