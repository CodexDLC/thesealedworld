from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any

from src.backend.features.rift.runtime.navigation import (
    resolve_node_entry_event_runtime,
    resolve_transition_combat_runtime,
)
from src.backend.infrastructure.rift.managers import RiftInstanceNotFoundError, RiftRunSessionNotFoundError
from src.backend.infrastructure.rift.mappers import RiftInstanceStateMapper, RiftRunStateMapper

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftZoneRuntimeDTO
    from src.backend.infrastructure.rift.managers import (
        RiftInstanceStore,
        RiftPortalStore,
        RiftPresenceStore,
        RiftRunSessionStore,
    )
    from src.backend.infrastructure.rift.models import RiftInstanceState, RiftRunState
    from src.backend.infrastructure.rift.repositories import (
        RiftInstanceStateRepository,
        RiftPortalKeyRepository,
        RiftRunStateRepository,
    )

RiftPersistenceMode = str


class RiftRuntimeNotFoundError(RuntimeError):
    pass


class RiftRuntimeIntegration:
    def __init__(
        self,
        *,
        instance_store: RiftInstanceStore,
        session_store: RiftRunSessionStore,
        presence_store: RiftPresenceStore,
        portal_store: RiftPortalStore | None = None,
        instance_state_repository: RiftInstanceStateRepository | None = None,
        run_state_repository: RiftRunStateRepository | None = None,
        portal_key_repository: RiftPortalKeyRepository | None = None,
        instance_state_mapper: RiftInstanceStateMapper | None = None,
        run_state_mapper: RiftRunStateMapper | None = None,
    ) -> None:
        self.instance_store = instance_store
        self.session_store = session_store
        self.presence_store = presence_store
        self.portal_store = portal_store
        self.instance_state_repository = instance_state_repository
        self.run_state_repository = run_state_repository
        self.portal_key_repository = portal_key_repository
        self.instance_state_mapper = instance_state_mapper or RiftInstanceStateMapper()
        self.run_state_mapper = run_state_mapper or RiftRunStateMapper()

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        await self.instance_store.save_instance(runtime)

    async def save_instance_runtime(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        mode: RiftPersistenceMode = "redis_only",
        status: str = "active",
    ) -> RiftInstanceState | None:
        if mode not in {"redis_only", "db_only", "redis_and_db"}:
            raise ValueError(f"Unsupported rift persistence mode: {mode}")
        if mode in {"redis_only", "redis_and_db"}:
            await self.instance_store.save_instance(runtime)
        if mode in {"db_only", "redis_and_db"}:
            return await self.backup_instance_state(runtime, status=status)
        return None

    async def backup_instance_state(self, runtime: RiftZoneRuntimeDTO, *, status: str = "active") -> RiftInstanceState:
        if self.instance_state_repository is None:
            raise RuntimeError("Rift instance state repository is not configured")
        state = self.instance_state_mapper.to_model(runtime, status=status)
        return await self.instance_state_repository.upsert(state)

    async def require_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO:
        try:
            return await self.instance_store.require_instance(rift_instance_id)
        except RiftInstanceNotFoundError as exc:
            if self.instance_state_repository is not None:
                state = await self.instance_state_repository.get(rift_instance_id)
                if state is not None:
                    runtime = self.instance_state_mapper.to_runtime(state)
                    await self.instance_store.save_instance(runtime)
                    return runtime
            raise RiftRuntimeNotFoundError(str(exc)) from exc

    async def patch_node_event(self, rift_instance_id: str, node_id: str, event: dict[str, Any]) -> None:
        await self.instance_store.patch_node_event(rift_instance_id, node_id, event)

    async def mark_node_cleared(self, rift_instance_id: str, node_id: str) -> None:
        await self.instance_store.mark_node_cleared(rift_instance_id, node_id)

    async def set_gate_state(self, rift_instance_id: str, gate_key: str, state: dict[str, Any]) -> None:
        await self.instance_store.set_gate_state(rift_instance_id, gate_key, state)

    async def set_heart_state(self, rift_instance_id: str, state: dict[str, Any]) -> None:
        await self.instance_store.set_heart_state(rift_instance_id, state)

    async def create_run_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.session_store.create_session(payload)

    async def create_portal(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        saved_payload: dict[str, Any] | None = None
        if self.portal_store is None:
            saved_payload = dict(payload)
        else:
            saved_payload = await self.portal_store.save_portal(payload)
        if self.portal_key_repository is not None:
            await self.portal_key_repository.upsert_from_payload(saved_payload)
        return saved_payload

    async def mark_portal_status(
        self,
        *,
        portal_id: str,
        status: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if self.portal_store is None:
            if self.portal_key_repository is not None:
                await self.portal_key_repository.mark_status(portal_id, status=status, reason=reason, details=details)
            return None
        updated = await self.portal_store.mark_status(portal_id, status=status, reason=reason, details=details)
        if updated is not None and self.portal_key_repository is not None:
            await self.portal_key_repository.upsert_from_payload(updated)
        elif self.portal_key_repository is not None:
            await self.portal_key_repository.mark_status(portal_id, status=status, reason=reason, details=details)
        return updated

    async def mark_portal_status_by_session(
        self,
        *,
        rift_session_id: str,
        status: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if self.portal_store is None:
            if self.portal_key_repository is None:
                return None
            portal = await self.portal_key_repository.get_by_rift_session(rift_session_id)
            if portal is None:
                return None
            await self.portal_key_repository.mark_status(
                portal.portal_id,
                status=status,
                reason=reason,
                details=details,
            )
            return None
        portal = await self.portal_store.find_by_rift_session(rift_session_id)
        if portal is None:
            return None
        return await self.mark_portal_status(
            portal_id=str(portal["portal_id"]),
            status=status,
            reason=reason,
            details=details,
        )

    async def archive_due_portals(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if self.portal_store is None:
            return []
        return await self.portal_store.archive_due(limit=limit)

    async def save_run_session(self, payload: dict[str, Any]) -> None:
        await self.session_store.save_session(
            payload,
            dirty_reason=str(payload.get("dirty_reason") or "run_session_saved"),
            dirty_paths=_dirty_paths_from_session_payload(payload),
        )

    async def save_run_session_runtime(
        self,
        payload: dict[str, Any],
        *,
        mode: RiftPersistenceMode = "redis_only",
        status: str | None = None,
    ) -> RiftRunState | None:
        if mode not in {"redis_only", "db_only", "redis_and_db"}:
            raise ValueError(f"Unsupported rift persistence mode: {mode}")
        if mode in {"redis_only", "redis_and_db"}:
            await self.session_store.save_session(payload)
        if mode in {"db_only", "redis_and_db"}:
            return await self.backup_run_state(payload, status=status)
        return None

    async def backup_run_state(self, payload: dict[str, Any], *, status: str | None = None) -> RiftRunState:
        if self.run_state_repository is None:
            raise RuntimeError("Rift run state repository is not configured")
        state = self.run_state_mapper.from_session_payload(payload, status=status)
        return await self.run_state_repository.upsert(state)

    async def get_run_session(self, rift_session_id: str) -> dict[str, Any] | None:
        return await self.session_store.get_session(rift_session_id)

    async def require_run_session(self, rift_session_id: str) -> dict[str, Any]:
        try:
            return await self.session_store.require_session(rift_session_id)
        except RiftRunSessionNotFoundError as exc:
            if self.run_state_repository is not None:
                state = await self.run_state_repository.get(rift_session_id)
                if state is not None:
                    payload = self.run_state_mapper.to_session_payload(state)
                    await self.session_store.create_session(payload)
                    return payload
            raise RiftRuntimeNotFoundError(str(exc)) from exc

    async def scan_dirty_run_sessions(self, *, limit: int = 100) -> list[str]:
        return await self.session_store.scan_dirty(limit=limit)

    async def flush_dirty_run_session(self, rift_session_id: str) -> dict[str, Any]:
        session = await self.require_run_session(rift_session_id)
        dirty = dict(session.get("dirty") or {})
        if session.get("is_dirty") is not True and dirty.get("dirty") is not True:
            return {"status": "skipped", "reason": "clean_session", "rift_session_id": rift_session_id}

        rift_instance_id = str(session.get("rift_instance_id") or "")
        if not rift_instance_id:
            return {"status": "skipped", "reason": "missing_rift_instance_id", "rift_session_id": rift_session_id}

        instance = await self.require_instance(rift_instance_id)
        await self.backup_instance_state(instance, status="active")
        await self.backup_run_state(session, status=str(session.get("status") or "active"))
        await self.session_store.clear_dirty(rift_session_id)
        return {
            "status": "ok",
            "rift_session_id": rift_session_id,
            "rift_instance_id": rift_instance_id,
        }

    async def set_run_position(
        self,
        rift_session_id: str,
        *,
        current_node_id: str,
        previous_node_id: str | None = None,
        heading: str | None = None,
    ) -> None:
        await self.session_store.set_position(
            rift_session_id,
            current_node_id=current_node_id,
            previous_node_id=previous_node_id,
            heading=heading,
        )

    async def set_run_visited(self, rift_session_id: str, node_ids: set[str]) -> None:
        await self.session_store.set_visited(rift_session_id, node_ids)

    async def set_run_discovered(self, rift_session_id: str, node_ids: set[str]) -> None:
        await self.session_store.set_discovered(rift_session_id, node_ids)

    async def start_run_travel(self, rift_session_id: str, travel: dict[str, Any]) -> None:
        await self.session_store.start_travel(rift_session_id, travel)

    async def interrupt_run_travel(self, rift_session_id: str, travel: dict[str, Any]) -> None:
        await self.session_store.interrupt_travel(rift_session_id, travel)

    async def complete_run_travel(self, rift_session_id: str, *, last_travel: dict[str, Any]) -> None:
        await self.session_store.complete_travel(rift_session_id, last_travel=last_travel)

    async def set_run_active_encounter(self, rift_session_id: str, encounter_id: str) -> None:
        await self.session_store.set_active_encounter(rift_session_id, encounter_id)

    async def clear_run_active_encounter(self, rift_session_id: str) -> None:
        await self.session_store.clear_active_encounter(rift_session_id)

    async def delete_run_session(self, rift_session_id: str) -> None:
        delete_session = getattr(self.session_store, "delete_session", None)
        if delete_session is not None:
            await delete_session(rift_session_id)

    async def abandon_run_for_deleted_character(
        self,
        *,
        rift_session_id: str,
        rift_instance_id: str,
        char_id: int,
    ) -> dict[str, Any]:
        session = await self.get_run_session(rift_session_id)
        participant_ref = f"char:{char_id}"
        current_node_id = ""
        if isinstance(session, dict):
            participant_ref = str(session.get("participant_ref") or participant_ref)
            current_node_id = str(session.get("current_node_id") or "")
            session = {
                **session,
                "status": "abandoned_deleted_character",
                "exit_result": {
                    "reason": "character_deleted",
                    "character_id": char_id,
                    "close_rift_on_exit": True,
                },
            }
            try:
                await self.save_run_session_runtime(
                    session,
                    mode="redis_and_db",
                    status="abandoned_deleted_character",
                )
            except RuntimeError:
                await self.save_run_session(session)
        await self.mark_portal_status_by_session(
            rift_session_id=rift_session_id,
            status="abandoned",
            reason="character_deleted",
            details={"character_id": char_id, "rift_instance_id": rift_instance_id},
        )
        if current_node_id:
            with suppress(Exception):
                await self.leave_node_presence(rift_instance_id, current_node_id, participant_ref)
        await self.delete_run_session(rift_session_id)
        return {
            "status": "abandoned",
            "rift_session_id": rift_session_id,
            "rift_instance_id": rift_instance_id,
        }

    async def apply_combat_result(
        self,
        *,
        combat_id: str,
        result: str,
        rift_session_id: str,
        rift_instance_id: str | None = None,
        event_scope: str | None = None,
        travel_id: str | None = None,
        event_key: str | None = None,
        participant_ref: str | None = None,
    ) -> dict[str, Any]:
        """Apply a finalized combat result to the owning rift runtime state."""
        if result != "victory":
            return {"applied": False, "reason": "unsupported_result"}

        session = await self.require_run_session(rift_session_id)
        combat_id = str(combat_id or session.get("active_encounter_id") or "")
        active_encounter_id = str(session.get("active_encounter_id") or "")
        if not active_encounter_id:
            return {"applied": False, "reason": "rift_encounter_already_resolved"}
        if active_encounter_id != combat_id:
            return {"applied": False, "reason": "rift_encounter_mismatch"}

        resolved_instance_id = str(rift_instance_id or session.get("rift_instance_id") or "")
        if not resolved_instance_id:
            return {"applied": False, "reason": "missing_rift_instance_id"}
        instance = await self.require_instance(resolved_instance_id)
        runtime = _runtime_for_run_session(instance, session)
        scope = str(event_scope or _active_event_scope(runtime) or "")

        if scope == "transition":
            resolved_travel_id = str(travel_id or dict(runtime.active_travel or {}).get("travel_id") or "")
            updated, _response = resolve_transition_combat_runtime(
                runtime,
                travel_id=resolved_travel_id,
                result=result,
            )
        elif scope in {"node_entry", "heart_guard", "boss", "boss_solo", "boss_with_minions"}:
            updated, _response = resolve_node_entry_event_runtime(
                runtime,
                event_key=event_key or None,
                result=result,
            )
            resolved_travel_id = ""
        else:
            await self._clear_resolved_encounter(
                session=session,
                combat_id=combat_id,
                rift_instance_id=resolved_instance_id,
                travel_id=travel_id,
            )
            return {"applied": False, "reason": "unsupported_rift_event_scope", "event_scope": scope}

        next_session = _session_payload_from_runtime(updated, previous_session=session, active_encounter_id=None)
        await self.save_instance(_instance_runtime_after_update(instance, updated))
        await self.save_run_session(next_session)

        previous_node_id = str(session.get("current_node_id") or "") or None
        current_node_id = str(next_session.get("current_node_id") or "") or None
        resolved_participant_ref = str(participant_ref or next_session.get("participant_ref") or "")
        if current_node_id and resolved_participant_ref and current_node_id != previous_node_id:
            await self.move_presence(
                updated.rift_instance_id,
                from_node_id=previous_node_id,
                to_node_id=current_node_id,
                participant_ref=resolved_participant_ref,
            )
        await self._clear_resolved_encounter(
            session=next_session,
            combat_id=combat_id,
            rift_instance_id=updated.rift_instance_id,
            travel_id=resolved_travel_id or travel_id,
        )
        return {
            "applied": True,
            "event_scope": scope,
            "rift_session_id": rift_session_id,
            "rift_instance_id": updated.rift_instance_id,
            "current_node_id": current_node_id,
        }

    async def _clear_resolved_encounter(
        self,
        *,
        session: dict[str, Any],
        combat_id: str,
        rift_instance_id: str,
        travel_id: str | None = None,
    ) -> None:
        await self.clear_run_active_encounter(str(session.get("rift_session_id") or ""))
        await self.clear_transition_encounter_presence(rift_instance_id, combat_id)
        if travel_id:
            await self.clear_transition_travel_presence(rift_instance_id, str(travel_id))

    async def enter_node_presence(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        await self.presence_store.enter_node(rift_instance_id, node_id, participant_ref)

    async def leave_node_presence(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        await self.presence_store.leave_node(rift_instance_id, node_id, participant_ref)

    async def move_presence(
        self,
        rift_instance_id: str,
        *,
        from_node_id: str | None,
        to_node_id: str,
        participant_ref: str,
    ) -> None:
        await self.presence_store.move_node(
            rift_instance_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            participant_ref=participant_ref,
        )

    async def get_node_occupants(self, rift_instance_id: str, node_id: str) -> set[str]:
        return await self.presence_store.get_node_occupants(rift_instance_id, node_id)

    async def join_transition_travel(self, rift_instance_id: str, travel_id: str, participant_ref: str) -> None:
        await self.presence_store.join_travel(rift_instance_id, travel_id, participant_ref)

    async def leave_transition_travel(self, rift_instance_id: str, travel_id: str, participant_ref: str) -> None:
        await self.presence_store.leave_travel(rift_instance_id, travel_id, participant_ref)

    async def get_transition_travel_participants(self, rift_instance_id: str, travel_id: str) -> set[str]:
        return await self.presence_store.get_travel_participants(rift_instance_id, travel_id)

    async def join_transition_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        await self.presence_store.join_encounter(rift_instance_id, encounter_id, participant_ref)

    async def leave_transition_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        await self.presence_store.leave_encounter(rift_instance_id, encounter_id, participant_ref)

    async def get_transition_encounter_participants(self, rift_instance_id: str, encounter_id: str) -> set[str]:
        return await self.presence_store.get_encounter_participants(rift_instance_id, encounter_id)

    async def clear_node_presence(self, rift_instance_id: str, node_id: str) -> None:
        await self.presence_store.clear_node_presence(rift_instance_id, node_id)

    async def clear_transition_travel_presence(self, rift_instance_id: str, travel_id: str) -> None:
        await self.presence_store.clear_travel_presence(rift_instance_id, travel_id)

    async def clear_transition_encounter_presence(self, rift_instance_id: str, encounter_id: str) -> None:
        await self.presence_store.clear_encounter_presence(rift_instance_id, encounter_id)


def _runtime_for_run_session(instance: RiftZoneRuntimeDTO, session: dict[str, Any]) -> RiftZoneRuntimeDTO:
    setting = dict(instance.setting or {})
    if isinstance(session.get("exit_policy"), dict):
        setting["exit_policy"] = session["exit_policy"]
    return instance.model_copy(
        update={
            "setting": setting,
            "zone_instance_id": session.get("zone_instance_id") or instance.zone_instance_id,
            "current_zone_key": session.get("current_zone_key") or instance.current_zone_key,
            "current_node_id": session.get("current_node_id") or instance.current_node_id,
            "previous_node_id": session.get("previous_node_id"),
            "heading": session.get("heading"),
            "visited_node_ids": set(session.get("visited_node_ids") or instance.visited_node_ids),
            "active_travel": session.get("active_travel"),
            "last_travel": session.get("last_travel"),
        }
    )


def _instance_runtime_after_update(
    previous_instance: RiftZoneRuntimeDTO,
    updated: RiftZoneRuntimeDTO,
) -> RiftZoneRuntimeDTO:
    zone_changed = (
        previous_instance.zone_instance_id != updated.zone_instance_id
        or previous_instance.current_zone_key != updated.current_zone_key
    )
    if zone_changed:
        return updated.model_copy(
            update={
                "current_node_id": updated.start_node_id,
                "previous_node_id": None,
                "heading": updated.heading,
                "visited_node_ids": {updated.start_node_id},
                "active_travel": None,
                "last_travel": None,
            }
        )
    return updated.model_copy(
        update={
            "current_node_id": previous_instance.current_node_id,
            "previous_node_id": previous_instance.previous_node_id,
            "heading": previous_instance.heading,
            "visited_node_ids": previous_instance.visited_node_ids,
            "active_travel": None,
            "last_travel": previous_instance.last_travel,
        }
    )


def _session_payload_from_runtime(
    runtime: RiftZoneRuntimeDTO,
    *,
    previous_session: dict[str, Any],
    active_encounter_id: str | None,
) -> dict[str, Any]:
    existing = dict(previous_session or {})
    return {
        **existing,
        "rift_instance_id": runtime.rift_instance_id,
        "zone_instance_id": runtime.zone_instance_id,
        "current_zone_key": runtime.current_zone_key,
        "current_node_id": runtime.current_node_id,
        "previous_node_id": runtime.previous_node_id,
        "heading": runtime.heading,
        "visited_node_ids": sorted(runtime.visited_node_ids),
        "discovered_node_ids": sorted(runtime.visited_node_ids),
        "active_travel": runtime.active_travel,
        "last_travel": runtime.last_travel,
        "active_encounter_id": active_encounter_id,
    }


def _dirty_paths_from_session_payload(payload: dict[str, Any]) -> list[str]:
    tracked_paths = [
        "$.rift_instance_id",
        "$.zone_instance_id",
        "$.current_zone_key",
        "$.current_node_id",
        "$.previous_node_id",
        "$.heading",
        "$.visited_node_ids",
        "$.discovered_node_ids",
        "$.active_travel",
        "$.last_travel",
        "$.active_encounter_id",
        "$.status",
        "$.exit_result",
    ]
    return [path for path in tracked_paths if path.removeprefix("$.") in payload]


def _active_event_scope(runtime: RiftZoneRuntimeDTO) -> str | None:
    active_travel = dict(runtime.active_travel or {})
    if active_travel.get("status") == "interrupted" and active_travel.get("tick_result") == "combat":
        return str(active_travel.get("event_scope") or "transition")
    event = dict(runtime.node_events.get(runtime.current_node_id) or {})
    if event.get("event_type") == "combat" and event.get("state", "ready") != "cleared":
        return "node_entry"
    return None
