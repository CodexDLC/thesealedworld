from __future__ import annotations

import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.backend.features.rift.dto import RiftStartRequestDTO
from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.services.dev_service import RiftDevService
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftZoneRuntimeDTO
    from src.backend.features.rift.integrations import RiftRuntimeIntegration
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager


class RiftEntryService:
    """Creates player rift runs and attaches them to the active character session."""

    def __init__(
        self,
        *,
        runtime: RiftRuntimeIntegration,
        character_sessions: CharacterSessionManager,
        resources: RiftResourceLoader | None = None,
        rift_key: str = "starter_rift",
        rift_population_bindings: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    ) -> None:
        self.runtime = runtime
        self.character_sessions = character_sessions
        self.resources = resources or RiftResourceLoader()
        self.rift_key = rift_key
        self.rift_population_bindings = rift_population_bindings or {}

    async def enter_from_scenario(
        self,
        *,
        char_id: int,
        source_ref: str,
        request: RiftStartRequestDTO | None = None,
    ) -> dict[str, Any]:
        start_request = request or RiftStartRequestDTO(debug=False)
        runtime = self._build_runtime(start_request)
        rift_session_id = f"rift:run:{uuid4().hex}"
        participant_ref = f"char:{char_id}"
        entry_context = {
            "source_state": CoreDomain.SCENARIO.value,
            "source_ref": source_ref,
            "combat_power": await self._entry_power_context(char_id),
        }

        await self.runtime.save_instance_runtime(runtime, mode="redis_and_db", status="active")
        session = self._session_payload_from_runtime(
            runtime,
            rift_session_id=rift_session_id,
            char_id=char_id,
            participant_ref=participant_ref,
            entry_context=entry_context,
            exit_policy={
                "target_state": CoreDomain.EXPLORATION.value,
                "location_id": None,
                "reason": "rift_exit",
                "completion_exit": "from_heart",
            },
        )
        await self.runtime.save_run_session_runtime(session, mode="redis_and_db", status="active")
        await self.runtime.enter_node_presence(runtime.rift_instance_id, runtime.current_node_id, participant_ref)
        await self.character_sessions.set_rift_session(
            char_id,
            str(session["rift_session_id"]),
            rift_instance_id=runtime.rift_instance_id,
            prev_state=CoreDomain.SCENARIO,
        )

        return {
            "status": "ok",
            "char_id": char_id,
            "target_state": CoreDomain.RIFT.value,
            "rift_instance_id": runtime.rift_instance_id,
            "rift_session_id": str(session["rift_session_id"]),
            "entry_context": entry_context,
        }

    async def prepare_from_scenario(
        self,
        *,
        char_id: int,
        source_ref: str,
        request_id: str,
        exit_policy: dict[str, Any],
        request: RiftStartRequestDTO | None = None,
        rift_key: str | None = None,
        entry_reason: str | None = None,
    ) -> dict[str, Any]:
        start_request = request or RiftStartRequestDTO(debug=False)
        runtime = self._build_runtime(start_request, rift_key=rift_key)
        rift_session_id = f"rift:run:{uuid4().hex}"
        participant_ref = f"char:{char_id}"
        entry_context = {
            "source_state": CoreDomain.SCENARIO.value,
            "source_ref": source_ref,
            "entry_reason": entry_reason,
            "request_id": request_id,
            "combat_power": await self._entry_power_context(char_id),
        }

        await self.runtime.save_instance_runtime(runtime, mode="redis_and_db", status="active")
        session = self._session_payload_from_runtime(
            runtime,
            rift_session_id=rift_session_id,
            char_id=char_id,
            participant_ref=participant_ref,
            entry_context=entry_context,
            exit_policy=exit_policy,
        )
        await self.runtime.save_run_session_runtime(session, mode="redis_and_db", status="active")
        await self.runtime.enter_node_presence(runtime.rift_instance_id, runtime.current_node_id, participant_ref)
        await self.character_sessions.attach_prepared_rift_session(
            char_id,
            str(session["rift_session_id"]),
            rift_instance_id=runtime.rift_instance_id,
            request_id=request_id,
        )
        create_portal = getattr(self.runtime, "create_portal", None)
        if create_portal is not None:
            await create_portal(
                {
                    "portal_id": request_id,
                    "source": "scenario",
                    "source_ref": source_ref,
                    "rift_key": rift_key or self.rift_key,
                    "entry_reason": entry_reason,
                    "owner_type": "character",
                    "owner_id": f"char:{char_id}",
                    "participant_scope": "solo",
                    "rift_session_id": str(session["rift_session_id"]),
                    "rift_instance_id": runtime.rift_instance_id,
                    "entry_mode": "prepared_activation",
                    "exit_policy": exit_policy,
                    "status": "active",
                    "expires_at": None,
                    "created_at": time.time(),
                }
            )

        return {
            "status": "ok",
            "char_id": char_id,
            "target_state": CoreDomain.SCENARIO.value,
            "rift_prepared": True,
            "rift_instance_id": runtime.rift_instance_id,
            "rift_session_id": str(session["rift_session_id"]),
            "entry_context": entry_context,
            "exit_policy": exit_policy,
        }

    async def handle_entry_requested(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            char_id = int(payload["char_id"])
            request = RiftStartRequestDTO(
                seed=_optional_str(payload.get("seed")),
                scale_preset_key=_optional_str(payload.get("scale_preset_key")),
                assembly_preset_key=_optional_str(payload.get("assembly_preset_key")),
                void_cells=_optional_int(payload.get("void_cells")),
                debug=False,
            )
            request_id = str(payload.get("request_id") or payload.get("correlation_id") or uuid4().hex)
            return await self.prepare_from_scenario(
                char_id=char_id,
                source_ref=str(payload.get("source_ref") or "scenario"),
                request_id=request_id,
                rift_key=_optional_str(payload.get("rift_key")),
                entry_reason=_optional_str(payload.get("entry_reason")),
                exit_policy={
                    "target_state": str(payload.get("exit_target_state") or CoreDomain.EXPLORATION.value),
                    "location_id": _optional_str(payload.get("exit_location_id")),
                    "reason": str(payload.get("exit_reason") or "rift_exit"),
                    "completion_exit": _optional_str(payload.get("completion_exit"))
                    or _optional_str(payload.get("exit_completion")),
                    "exit_node_id": _optional_str(payload.get("exit_node_id")),
                },
                request=request,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "error": f"{exc.__class__.__name__}: {exc}",
                "target_state": CoreDomain.SCENARIO.value,
            }

    def _build_runtime(self, request: RiftStartRequestDTO, *, rift_key: str | None = None) -> RiftZoneRuntimeDTO:
        runtime = RiftDevService(
            runtime=self.runtime,
            resources=self.resources,
            rift_key=rift_key or self.rift_key,
        ).build_runtime(request)
        return runtime.model_copy(update={"debug": False, "dev_character_snapshot": {}})

    async def _entry_power_context(self, char_id: int) -> dict[str, Any]:
        getter = getattr(self.character_sessions, "get_session", None)
        session = await getter(char_id) if getter is not None else None
        metrics = dict(session.get("metrics") or {}) if isinstance(session, dict) else {}
        gear_score = _non_negative_int(metrics.get("gear_score"))
        return {
            "scope": "solo",
            "player_gear_score": gear_score,
            "party_gear_score": gear_score,
            "source": "active_character.metrics.gear_score",
        }

    @staticmethod
    def _session_payload_from_runtime(
        runtime: RiftZoneRuntimeDTO,
        *,
        rift_session_id: str,
        char_id: int,
        participant_ref: str,
        entry_context: dict[str, Any],
        exit_policy: dict[str, Any],
    ) -> dict[str, Any]:
        requested_exit_policy = {key: value for key, value in exit_policy.items() if value is not None}
        return {
            "rift_session_id": rift_session_id,
            "owner_type": "character",
            "owner_id": f"char:{char_id}",
            "participant_scope": "solo",
            "participant_ref": participant_ref,
            "rift_instance_id": runtime.rift_instance_id,
            "setting_key": str(dict(runtime.setting or {}).get("setting_key") or "starter_rift"),
            "source": _optional_str(entry_context.get("source_state")),
            "source_ref": _optional_str(entry_context.get("source_ref")),
            "zone_instance_id": runtime.zone_instance_id,
            "current_zone_key": runtime.current_zone_key,
            "current_node_id": runtime.current_node_id,
            "previous_node_id": runtime.previous_node_id,
            "heading": runtime.heading,
            "visited_node_ids": sorted(runtime.visited_node_ids),
            "discovered_node_ids": sorted(runtime.visited_node_ids),
            "active_travel": None,
            "last_travel": None,
            "active_encounter_id": None,
            "entry_context": entry_context,
            "exit_policy": _normalized_exit_policy(
                {**dict(runtime.setting.get("exit_policy") or {}), **requested_exit_policy},
                start_node_id=runtime.start_node_id,
            ),
            "return_policy": "escape_only",
        }


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _normalized_exit_policy(exit_policy: dict[str, Any], *, start_node_id: str) -> dict[str, Any]:
    raw = dict(exit_policy or {})
    mode = str(raw.get("mode") or "heart_exit_only")
    if mode not in {"entrance_return_only", "heart_exit_only"}:
        mode = "heart_exit_only"
    completion_exit = str(raw.get("completion_exit") or "from_heart")
    if completion_exit not in {"from_heart", "return_to_exit"}:
        completion_exit = "from_heart"
    entrance_node_id = str(raw.get("entrance_node_id") or start_node_id)
    return {
        **raw,
        "mode": mode,
        "completion_exit": completion_exit,
        "entrance_seals_on_entry": bool(raw.get("entrance_seals_on_entry", mode == "heart_exit_only")),
        "entrance_node_id": entrance_node_id,
        "exit_node_id": str(raw.get("exit_node_id") or entrance_node_id),
        "target_state": str(raw.get("target_state") or CoreDomain.EXPLORATION.value),
        "location_id": _optional_str(raw.get("location_id")),
        "close_rift_on_exit": bool(raw.get("close_rift_on_exit", True)),
    }
