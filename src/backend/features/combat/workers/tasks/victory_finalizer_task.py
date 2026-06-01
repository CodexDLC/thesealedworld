from typing import Any

from loguru import logger as log

from src.backend.core.database import get_session_context
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.combat.runtime.services.durability_policy import CombatDurabilityPolicy
from src.backend.features.combat.runtime.services.experience_finalizer import CombatExperienceFinalizer
from src.backend.features.combat.runtime.services.finalization_builder import CombatFinalizationBuilder
from src.backend.features.combat.services.post_battle_router import CombatPostBattleRouter
from src.backend.features.combat.workers.tasks.chat_announcements import publish_combat_final_announcement
from src.backend.features.expedition import ExpeditionService
from src.backend.features.inventory.events.publisher import InventoryEvents
from src.backend.infrastructure.loot.managers.loot_manager import LootManager
from src.backend.infrastructure.rift.managers import (
    RiftInstanceStore,
    RiftPortalStore,
    RiftPresenceStore,
    RiftRunSessionStore,
)
from src.backend.infrastructure.rift.repositories import (
    RiftInstanceStateRepository,
    RiftPortalKeyRepository,
    RiftRunStateRepository,
)
from src.backend.realtime.integrations.notice_publisher import (
    PlayerNoticePublisher,
    RawStreamNoticeProducer,
    RefreshTargets,
)
from src.shared.enums import CoreDomain
from src.shared.infrastructure.log_task_wrapper import logged_task


def _build_notice_publisher(ctx: dict) -> PlayerNoticePublisher | None:
    redis = ctx.get("redis_client_internal")
    if redis is None:
        return None
    return PlayerNoticePublisher(RawStreamNoticeProducer(redis))


@logged_task
async def victory_finalizer_task(ctx: dict, data: dict) -> None:
    """
    Финализатор боя (Victory Finalizer).

    Выполняется после определения победителя.
    Отвечает за завершение боя и начисление наград.

    Args:
        ctx: ARQ worker context with runtime, persistence, and cross-feature deps.
        data: Finalization payload containing ``session_id`` and ``winner``.

    Side Effects:
        - Marks the winner in runtime storage.
        - Finalizes XP/progression and persists frozen finalization payloads.
        - Commits post-combat outcomes back into active character sessions.
        - Enqueues the long-term finalization persistence job.
    """
    session_id = data.get("session_id", "unknown")
    winner = data.get("winner", "unknown")

    log.bind(session_id=session_id, winner=winner, status="processing").info("VictoryFinalizerStarted")

    data_service: CombatDataService | None = ctx.get("combat_data_service")
    if not data_service:
        log.bind(reason="no_data_service").error("VictoryFinalizerFailed")
        return

    try:
        # 1. Устанавливаем статус победы в Redis
        await data_service.set_battle_winner(session_id, winner)

        # 2. Commit final combat vitals back into the active character session.
        await _commit_player_vitals_to_active_sessions(ctx, data_service, session_id)

        # 3. Convert flat runtime xp_buffer counters into character progression rewards.
        global_rate = 0.00005
        game_config = ctx.get("game_config")
        if game_config is not None:
            global_rate = await game_config.get_float("core", "SKILL_PROGRESSION_BASE_RATE", default=0.00005)

        progression_recorder = None
        if ctx.get("expeditions") is not None or ctx.get("world_locations") is not None:
            async with get_session_context() as session:
                progression_recorder = ExpeditionService(
                    session=session,
                    character_sessions=ctx.get("character_sessions"),
                    expedition_manager=ctx.get("expeditions"),
                    world_store=ctx.get("world_locations"),
                    game_config=ctx.get("game_config"),
                )
                progression_results = await CombatExperienceFinalizer().finalize(
                    data_service,
                    session_id,
                    winner,
                    character_sessions=ctx.get("character_sessions"),
                    progression_recorder=progression_recorder,
                    global_rate=global_rate,
                )
        else:
            progression_results = await CombatExperienceFinalizer().finalize(
                data_service,
                session_id,
                winner,
                character_sessions=ctx.get("character_sessions"),
                progression_recorder=None,
                global_rate=global_rate,
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
            await _apply_rift_combat_result(ctx, finalization)
            await _apply_durability_consequences(ctx, finalization)
            await _attach_finalization_to_active_sessions(ctx, session_id, finalization)
            await publish_combat_final_announcement(ctx, finalization)
            await _enqueue_finalization_persist(ctx, session_id)

        log.bind(session_id=session_id).info("VictoryFinalizerCompleted")

    except Exception:  # noqa: BLE001
        log.bind(session_id=session_id).exception("VictoryFinalizerFailed")


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
                log.bind(
                    char_id=durability_request.char_id,
                    combat_id=durability_request.combat_id,
                    error=response.get("error"),
                ).warning("VictoryFinalizerDurabilityDamageFailed")
        except Exception:  # noqa: BLE001
            log.bind(
                char_id=durability_request.char_id,
                combat_id=durability_request.combat_id,
            ).exception("VictoryFinalizerDurabilityDamageRequestFailed")


async def _apply_rift_combat_result(ctx: dict, finalization: dict[str, Any]) -> None:
    meta = finalization.get("meta") if isinstance(finalization.get("meta"), dict) else {}
    battle_type = str(meta.get("battle_type") or "").lower()
    rift_session_id = str(meta.get("rift_session_id") or "")
    if battle_type != "rift" and not rift_session_id:
        return
    if not rift_session_id:
        log.bind(combat_id=finalization.get("combat_id")).warning("VictoryFinalizerRiftResultMissingSession")
        return

    result = _resolve_rift_result(finalization)

    rift_runtime = ctx.get("rift_runtime")
    db_session_cm = None
    if rift_runtime is None:
        redis_service = ctx.get("redis_service")
        if redis_service is None:
            log.bind(combat_id=finalization.get("combat_id")).warning("VictoryFinalizerRiftRuntimeUnavailable")
            return
        from src.backend.features.rift.integrations import RiftRuntimeIntegration

        # Build the full runtime integration so DB fallback for require_instance /
        # require_run_session works, and so portal status can be marked on defeat.
        db_session_cm = get_session_context()
        db_session = await db_session_cm.__aenter__()
        rift_runtime = RiftRuntimeIntegration(
            instance_store=RiftInstanceStore(redis_service),
            session_store=RiftRunSessionStore(redis_service),
            presence_store=RiftPresenceStore(redis_service),
            portal_store=RiftPortalStore(redis_service),
            instance_state_repository=RiftInstanceStateRepository(db_session),
            run_state_repository=RiftRunStateRepository(db_session),
            portal_key_repository=RiftPortalKeyRepository(db_session),
        )

    try:
        apply_combat_result = getattr(rift_runtime, "apply_combat_result", None)
        if apply_combat_result is None:
            clear_run_active_encounter = getattr(rift_runtime, "clear_run_active_encounter", None)
            if clear_run_active_encounter is not None:
                await clear_run_active_encounter(rift_session_id)
            return

        await apply_combat_result(
            combat_id=str(finalization.get("combat_id") or ""),
            result=result,
            rift_session_id=rift_session_id,
            rift_instance_id=str(meta.get("rift_instance_id") or ""),
            event_scope=str(meta.get("rift_event_scope") or ""),
            travel_id=str(meta.get("rift_travel_id") or ""),
            event_key=str(meta.get("rift_event_key") or ""),
            participant_ref="",
        )
    finally:
        if db_session_cm is not None:
            await db_session_cm.__aexit__(None, None, None)


def _resolve_rift_result(finalization: dict[str, Any]) -> str:
    """Return ``victory`` if the winning team contained a player char_id, else ``defeat``.

    The previous implementation hardcoded ``victory``, which silently cleared rift
    node_events / opened gates even when monsters won the encounter.
    """
    winner_team = str(finalization.get("winner_team") or "")
    if not winner_team or winner_team == "draw":
        return "defeat"
    actors = finalization.get("actors") if isinstance(finalization.get("actors"), dict) else {}
    for actor in actors.values():
        if not isinstance(actor, dict):
            continue
        if actor.get("char_id") is None:
            continue
        if str(actor.get("team") or "") != winner_team:
            continue
        return "victory"
    return "defeat"


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
    notice_publisher = _build_notice_publisher(ctx)
    death_marked: set[int] = set()
    if dead_char_ids:
        async with get_session_context() as session:
            expedition_service = ExpeditionService(
                session=session,
                character_sessions=character_sessions,
                expedition_manager=ctx.get("expeditions"),
                loot_manager=LootManager(ctx["redis_service"]) if ctx.get("redis_service") is not None else None,
                world_store=ctx.get("world_locations"),
                commit_on_write=True,
                game_config=ctx.get("game_config"),
                notice_publisher=notice_publisher,
            )
            for char_id in dead_char_ids:
                if await expedition_service.mark_death_pending(
                    char_id=char_id,
                    combat_id=session_id,
                    location_id=str(location_id) if location_id else None,
                ):
                    await expedition_service.finalize_death_corpse(char_id=char_id)
                    death_marked.add(char_id)

    post_combat = await CombatPostBattleRouter().build_outcomes(ctx, finalization)
    for char_id in char_ids:
        outcome = post_combat.get(char_id)
        outcome_payload = outcome.model_dump(mode="json") if outcome is not None else None
        if char_id in death_marked:
            if outcome_payload is not None:
                await character_sessions.patch_fields(char_id, {"$.sessions.post_combat": outcome_payload})
                await character_sessions.mark_dirty(
                    char_id,
                    reason="combat_post_battle_outcome_attached",
                    paths=["$.sessions.post_combat"],
                )
            continue
        await character_sessions.patch_fields(
            char_id,
            {
                "$.sessions.combat_id": None,
                "$.sessions.combat_finalization_id": str(session_id),
                "$.sessions.post_combat": outcome_payload,
                "$.state": CoreDomain.COMBAT_RESULT.value,
            },
        )
        await character_sessions.mark_dirty(
            char_id,
            reason="combat_finalization_attached",
            paths=["$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.sessions.post_combat", "$.state"],
        )

    # Combat resolved without a direct player request — wake each participant's
    # HUD to re-fetch the status fragment (vitals/state changed in the worker).
    if notice_publisher is not None:
        for char_id in char_ids:
            await notice_publisher.request_refresh(
                char_id,
                target=RefreshTargets.STATUS,
                reason="combat_finalized",
                domain="combat",
            )


async def _commit_player_vitals_to_active_sessions(ctx: dict, data_service: CombatDataService, session_id: str) -> None:
    character_sessions = ctx.get("character_sessions")
    if character_sessions is None:
        log.bind(session_id=session_id).warning("VictoryFinalizerActiveCharacterSessionsUnavailable")
        return

    meta = await data_service.get_meta(session_id)
    if not isinstance(meta, dict):
        log.bind(session_id=session_id).warning("VictoryFinalizerCombatMetaUnavailable")
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
