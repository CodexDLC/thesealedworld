from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.rift.dto.screen import RiftExitResponseDTO, RiftTravelTickResponseDTO
from src.backend.features.rift.runtime.actions import resolve_rift_action_runtime
from src.backend.features.rift.runtime.navigation import build_rift_screen, start_travel_runtime, tick_travel_runtime
from src.backend.features.rift.runtime.tunables import load_rift_tunables, use_tunables
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.features.rift.dto import (
        RiftActionRequestDTO,
        RiftActionResponseDTO,
        RiftScreenDTO,
        RiftTravelStartRequestDTO,
        RiftTravelTickRequestDTO,
        RiftZoneRuntimeDTO,
    )
    from src.backend.features.rift.integrations import RiftRuntimeIntegration
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager
    from src.backend.infrastructure.game_config.manager import GameConfigManager


class RiftPlayerService:
    def __init__(
        self,
        *,
        runtime: RiftRuntimeIntegration,
        character_sessions: CharacterSessionManager,
        encounters: Any | None = None,
        game_config: GameConfigManager | None = None,
    ) -> None:
        self.runtime = runtime
        self.character_sessions = character_sessions
        self.encounters = encounters
        self.game_config = game_config

    async def screen(self, char_id: int) -> RiftScreenDTO:
        context = await self._exit_context(char_id)
        tunables = await load_rift_tunables(self.game_config)
        with use_tunables(tunables):
            return build_rift_screen(
                self._runtime_for_session(
                    context["instance"],
                    context["session"],
                    document=context["document"],
                )
            )

    async def start_travel(
        self,
        char_id: int,
        request: RiftTravelStartRequestDTO,
    ) -> RiftTravelTickResponseDTO:
        context = await self._exit_context(char_id)
        runtime = self._runtime_for_session(context["instance"], context["session"], document=context["document"])
        tunables = await load_rift_tunables(self.game_config)
        with use_tunables(tunables):
            updated, response = start_travel_runtime(runtime, request.target_node_id)
        await self._save_runtime_update(context=context, updated=updated)
        return response

    async def tick_travel(
        self,
        char_id: int,
        request: RiftTravelTickRequestDTO,
    ) -> RiftTravelTickResponseDTO:
        context = await self._exit_context(char_id)
        runtime = self._runtime_for_session(context["instance"], context["session"], document=context["document"])
        tunables = await load_rift_tunables(self.game_config)
        with use_tunables(tunables):
            updated, response = tick_travel_runtime(
                runtime, travel_id=request.travel_id, force_event=request.force_event
            )
        session = await self._save_runtime_update(context=context, updated=updated)
        if response.combat_prompt is not None and self.encounters is not None:
            response = response.model_copy(
                update={
                    "combat_prompt": await self.encounters.launch_combat_from_prompt(
                        updated,
                        session=session,
                        prompt=response.combat_prompt,
                    )
                }
            )
        return response

    async def run_action(
        self,
        char_id: int,
        request: RiftActionRequestDTO,
    ) -> RiftActionResponseDTO:
        context = await self._exit_context(char_id)
        runtime = self._runtime_for_session(context["instance"], context["session"], document=context["document"])
        if request.action_type == "resolve_node_event" and _current_node_combat_event(runtime):
            raise ValueError("Node combat must be resolved by combat result")
        tunables = await load_rift_tunables(self.game_config)
        with use_tunables(tunables):
            updated, response = resolve_rift_action_runtime(runtime, request)
        await self._save_runtime_update(context=context, updated=updated)
        return response

    async def leave(self, char_id: int) -> RiftExitResponseDTO:
        context = await self._exit_context(char_id)
        policy = _normalized_exit_policy(context["session"], start_node_id=context["instance"].start_node_id)
        if policy["mode"] != "entrance_return_only":
            raise ValueError("Rift leave is only available for entrance_return_only rifts")
        entrance_node_id = str(policy.get("entrance_node_id") or context["instance"].start_node_id)
        if str(context["session"].get("current_node_id") or "") != entrance_node_id:
            raise ValueError("Rift leave is only available from the entrance node")
        return await self._exit_rift(char_id, context=context, policy=policy, reason="left")

    async def complete(self, char_id: int) -> RiftExitResponseDTO:
        context = await self._exit_context(char_id)
        policy = _normalized_exit_policy(context["session"], start_node_id=context["instance"].start_node_id)
        if policy["mode"] != "heart_exit_only":
            raise ValueError("Rift completion is not available for this exit policy")
        runtime = self._runtime_for_session(context["instance"], context["session"])
        if not _completion_available(runtime):
            raise ValueError("Rift completion is not available before the objective is complete")
        if policy["completion_exit"] == "return_to_exit":
            exit_node_id = str(
                policy.get("exit_node_id") or policy.get("entrance_node_id") or context["instance"].start_node_id
            )
            if str(context["session"].get("current_node_id") or "") != exit_node_id:
                raise ValueError("Rift completion requires return to the rift exit")
        return await self._exit_rift(char_id, context=context, policy=policy, reason="completed")

    async def _rift_refs(self, char_id: int) -> dict[str, str]:
        document = await self.character_sessions.get_session(char_id)
        sessions = document.get("sessions") if isinstance(document, dict) else {}
        sessions = sessions if isinstance(sessions, dict) else {}
        rift_session_id = str(sessions.get("rift_session_id") or "")
        rift_instance_id = str(sessions.get("rift_instance_id") or "")
        if not rift_session_id or not rift_instance_id:
            raise ValueError(f"Character is not in an active rift: char_id={char_id}")
        return {"rift_session_id": rift_session_id, "rift_instance_id": rift_instance_id}

    async def _exit_context(self, char_id: int) -> dict[str, Any]:
        document = await self.character_sessions.get_session(char_id)
        sessions = document.get("sessions") if isinstance(document, dict) else {}
        sessions = sessions if isinstance(sessions, dict) else {}
        rift_session_id = str(sessions.get("rift_session_id") or "")
        rift_instance_id = str(sessions.get("rift_instance_id") or "")
        if not rift_session_id or not rift_instance_id:
            raise ValueError(f"Character is not in an active rift: char_id={char_id}")
        instance = await self.runtime.require_instance(rift_instance_id)
        session = await self.runtime.require_run_session(rift_session_id)
        if str(session.get("rift_instance_id") or "") != instance.rift_instance_id:
            raise ValueError("Rift run session does not belong to the active rift instance")
        return {
            "document": document,
            "instance": instance,
            "session": session,
            "rift_session_id": rift_session_id,
            "rift_instance_id": rift_instance_id,
        }

    async def _exit_rift(
        self,
        char_id: int,
        *,
        context: dict[str, Any],
        policy: dict[str, Any],
        reason: str,
    ) -> RiftExitResponseDTO:
        session = dict(context["session"])
        instance = context["instance"]
        rift_session_id = str(context["rift_session_id"])
        target_state = str(policy.get("target_state") or CoreDomain.EXPLORATION.value)
        location_id = str(policy.get("location_id") or "") or None
        participant_ref = str(session.get("participant_ref") or f"char:{char_id}")
        current_node_id = str(session.get("current_node_id") or instance.current_node_id)

        session.update(
            {
                "status": "completed" if reason == "completed" else "left",
                "exit_result": {
                    "reason": reason,
                    "target_state": target_state,
                    "location_id": location_id,
                    "close_rift_on_exit": bool(policy.get("close_rift_on_exit", True)),
                },
            }
        )
        if reason == "completed":
            symbiote_reward = await self._apply_symbiote_reward(char_id, context=context)
            if symbiote_reward:
                session["exit_result"]["symbiote_reward"] = symbiote_reward
        await self.runtime.save_run_session(session)
        mark_portal = getattr(self.runtime, "mark_portal_status_by_session", None)
        if mark_portal is not None:
            await mark_portal(
                rift_session_id=rift_session_id,
                status="completed" if reason == "completed" else "abandoned",
                reason=reason,
                details=session["exit_result"],
            )
        await self.runtime.leave_node_presence(instance.rift_instance_id, current_node_id, participant_ref)
        if location_id and hasattr(self.character_sessions, "set_location"):
            prev_location_id = _current_location_id(context.get("document"))
            await self.character_sessions.set_location(char_id, location_id, prev=prev_location_id)
        await self.character_sessions.set_state(char_id, target_state, prev_state=CoreDomain.RIFT.value)
        await self.character_sessions.clear_rift_session(char_id)

        return RiftExitResponseDTO(
            action="complete_rift" if reason == "completed" else "leave_rift",
            target_state=target_state,
            location_id=location_id,
            rift_session_id=rift_session_id,
            rift_instance_id=instance.rift_instance_id,
            exit_reason=reason,  # type: ignore[arg-type]
            close_rift_on_exit=bool(policy.get("close_rift_on_exit", True)),
            details=session["exit_result"],
        )

    async def _save_runtime_update(
        self,
        *,
        context: dict[str, Any],
        updated: RiftZoneRuntimeDTO,
    ) -> dict[str, Any]:
        instance = context["instance"]
        previous_session = dict(context["session"])
        await self.runtime.save_instance(self._instance_runtime_after_update(instance, updated))
        next_session = self._session_payload_from_runtime(updated, previous_session=previous_session)
        await self.runtime.save_run_session(next_session)
        previous_node_id = previous_session.get("current_node_id")
        current_node_id = next_session.get("current_node_id")
        participant_ref = str(next_session.get("participant_ref") or "")
        if current_node_id and participant_ref and current_node_id != previous_node_id:
            await self.runtime.move_presence(
                updated.rift_instance_id,
                from_node_id=previous_node_id,
                to_node_id=str(current_node_id),
                participant_ref=participant_ref,
            )
        return next_session

    async def _apply_symbiote_reward(self, char_id: int, *, context: dict[str, Any]) -> dict[str, Any]:
        instance = context["instance"]
        heart = dict(instance.heart_state or {})
        reward = dict(heart.get("reward") or {})
        amount = int(reward.get("symbiote_xp") or 0)
        if amount <= 0 or not hasattr(self.character_sessions, "apply_symbiote_xp"):
            return {}
        return await self.character_sessions.apply_symbiote_xp(char_id, amount)

    def _runtime_for_session(
        self,
        instance: RiftZoneRuntimeDTO,
        session: dict[str, Any],
        *,
        document: dict[str, Any] | None = None,
    ) -> RiftZoneRuntimeDTO:
        setting = dict(instance.setting or {})
        if isinstance(session.get("exit_policy"), dict):
            setting["exit_policy"] = _normalized_exit_policy(session, start_node_id=instance.start_node_id)
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
                "dev_character_snapshot": _character_snapshot_from_document(document),
            }
        )

    def _instance_runtime_after_update(
        self,
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
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        previous_session: dict[str, Any],
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
            "active_encounter_id": existing.get("active_encounter_id"),
        }


def _normalized_exit_policy(session: dict[str, Any], *, start_node_id: str) -> dict[str, Any]:
    raw = dict(session.get("exit_policy") or {})
    mode = str(raw.get("mode") or "heart_exit_only")
    if mode not in {"entrance_return_only", "heart_exit_only"}:
        mode = "heart_exit_only"
    completion_exit = str(raw.get("completion_exit") or "from_heart")
    if completion_exit not in {"from_heart", "return_to_exit"}:
        completion_exit = "from_heart"
    entrance_node_id = str(raw.get("entrance_node_id") or start_node_id)
    return {
        "mode": mode,
        "completion_exit": completion_exit,
        "entrance_seals_on_entry": bool(raw.get("entrance_seals_on_entry", mode == "heart_exit_only")),
        "entrance_node_id": entrance_node_id,
        "exit_node_id": str(raw.get("exit_node_id") or entrance_node_id),
        "target_state": str(raw.get("target_state") or CoreDomain.EXPLORATION.value),
        "location_id": str(raw.get("location_id") or "") or None,
        "close_rift_on_exit": bool(raw.get("close_rift_on_exit", True)),
    }


def _character_snapshot_from_document(document: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(document, dict):
        return {}
    attributes = document.get("attributes")
    if not isinstance(attributes, dict):
        return {}
    return {
        "character": {
            "attributes": {str(key): int(value) for key, value in attributes.items()},
        }
    }


def _completion_available(runtime: RiftZoneRuntimeDTO) -> bool:
    heart = dict(runtime.heart_state or {})
    completion = dict(heart.get("completion") or {})
    return (
        bool(heart.get("can_exit"))
        or str(completion.get("status") or "") == "completed"
        or str(heart.get("status") or "intact") != "intact"
    )


def _current_node_combat_event(runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
    event = dict(runtime.node_events.get(runtime.current_node_id) or {})
    if event.get("event_type") != "combat":
        return {}
    if event.get("state") != "ready":
        return {}
    return event


def _current_location_id(document: Any) -> str | None:
    if not isinstance(document, dict):
        return None
    location = document.get("location")
    if isinstance(location, dict):
        return str(location.get("current") or "") or None
    return None
