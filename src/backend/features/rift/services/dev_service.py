from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.runtime.generation import (
    build_zone_chain_runtime,
    build_zone_runtime,
    select_zone_assembly_plan,
)
from src.backend.features.rift.runtime.navigation import (
    build_rift_screen,
    resolve_rift_action_runtime,
    start_travel_runtime,
    tick_travel_runtime,
)

if TYPE_CHECKING:
    from src.backend.features.rift.dto import (
        RiftActionRequestDTO,
        RiftActionResponseDTO,
        RiftScreenDTO,
        RiftStartRequestDTO,
        RiftTravelStartRequestDTO,
        RiftTravelTickRequestDTO,
        RiftTravelTickResponseDTO,
        RiftZoneRuntimeDTO,
    )
    from src.backend.features.rift.integrations import RiftRuntimeIntegration

_DEV_OWNER_TYPE = "dev"
_DEV_OWNER_ID = "dev-character-rift-tester"
_DEV_PARTICIPANT_REF = "dev:dev-character-rift-tester"


class RiftDevService:
    def __init__(
        self,
        *,
        runtime: RiftRuntimeIntegration,
        resources: RiftResourceLoader | None = None,
        rift_key: str = "starter_rift",
        encounters: Any | None = None,
    ) -> None:
        self.runtime = runtime
        self.resources = resources or RiftResourceLoader()
        self.rift_key = rift_key
        self.encounters = encounters

    async def start(self, request: RiftStartRequestDTO) -> RiftScreenDTO:
        runtime = self.build_runtime(request)
        await self.runtime.save_instance(runtime)
        session = await self._reset_dev_run_session(runtime)
        return build_rift_screen(self._runtime_for_session(runtime, session))

    def build_runtime(self, request: RiftStartRequestDTO) -> RiftZoneRuntimeDTO:
        setting = self.resources.load_setting(self.rift_key)
        pool_nodes = self.resources.load_node_pool(self.rift_key)
        scale_preset, assembly_preset = select_zone_assembly_plan(
            setting=setting,
            scale_presets=self.resources.load_scale_presets(),
            assembly_presets=self.resources.load_zone_assembly_presets(),
            seed=request.seed,
            requested_scale_key=request.scale_preset_key,
            requested_assembly_preset_key=request.assembly_preset_key,
        )
        builder = (
            build_zone_chain_runtime
            if dict(assembly_preset.get("zone_chain") or {}).get("levels")
            else build_zone_runtime
        )
        runtime = builder(
            setting=setting,
            pool_nodes=pool_nodes,
            scale_preset=scale_preset,
            assembly_preset=assembly_preset,
            seed=request.seed,
            void_cells=request.void_cells,
            debug=request.debug,
        )
        return runtime.model_copy(update={"dev_character_snapshot": self.resources.load_dev_character_snapshot()})

    async def screen(self, rift_instance_id: str) -> RiftScreenDTO:
        runtime = await self.runtime.require_instance(rift_instance_id)
        session = await self._ensure_dev_run_session(runtime)
        return build_rift_screen(self._runtime_for_session(runtime, session))

    async def start_travel(
        self,
        rift_instance_id: str,
        request: RiftTravelStartRequestDTO,
    ) -> RiftTravelTickResponseDTO:
        instance = await self.runtime.require_instance(rift_instance_id)
        session = await self._ensure_dev_run_session(instance)
        runtime = self._runtime_for_session(instance, session)
        updated, response = start_travel_runtime(runtime, request.target_node_id)
        await self._save_runtime_update(instance=instance, previous_session=session, updated=updated)
        return response

    async def tick_travel(
        self,
        rift_instance_id: str,
        request: RiftTravelTickRequestDTO,
    ) -> RiftTravelTickResponseDTO:
        instance = await self.runtime.require_instance(rift_instance_id)
        session = await self._ensure_dev_run_session(instance)
        runtime = self._runtime_for_session(instance, session)
        updated, response = tick_travel_runtime(runtime, travel_id=request.travel_id, force_event=request.force_event)
        await self._save_runtime_update(instance=instance, previous_session=session, updated=updated)
        if response.combat_prompt is not None and self.encounters is not None:
            response = response.model_copy(
                update={
                    "combat_prompt": await self.encounters.enrich_combat_prompt(
                        updated,
                        session=session,
                        prompt=response.combat_prompt,
                    )
                }
            )
        return response

    async def run_action(
        self,
        rift_instance_id: str,
        request: RiftActionRequestDTO,
    ) -> RiftActionResponseDTO:
        instance = await self.runtime.require_instance(rift_instance_id)
        session = await self._ensure_dev_run_session(instance)
        runtime = self._runtime_for_session(instance, session)
        updated, response = resolve_rift_action_runtime(runtime, request)
        await self._save_runtime_update(instance=instance, previous_session=session, updated=updated)
        return response

    async def rebuild(
        self,
        rift_instance_id: str,
        *,
        seed: str | None,
        scale_preset_key: str | None = None,
        assembly_preset_key: str | None = None,
        void_cells: int | None,
    ) -> RiftScreenDTO:
        runtime = await self.runtime.require_instance(rift_instance_id)
        rebuild_seed = seed or f"{runtime.rift_instance_id}:rebuild:{uuid4().hex}"
        setting = self.resources.load_setting(self.rift_key)
        pool_nodes = self.resources.load_node_pool(self.rift_key)
        scale_preset, assembly_preset = select_zone_assembly_plan(
            setting=setting,
            scale_presets=self.resources.load_scale_presets(),
            assembly_presets=self.resources.load_zone_assembly_presets(),
            seed=rebuild_seed,
            requested_scale_key=scale_preset_key,
            requested_assembly_preset_key=assembly_preset_key,
            use_default_scale=scale_preset_key is not None,
        )
        builder = (
            build_zone_chain_runtime
            if dict(assembly_preset.get("zone_chain") or {}).get("levels")
            else build_zone_runtime
        )
        updated = builder(
            setting=setting,
            pool_nodes=pool_nodes,
            scale_preset=scale_preset,
            assembly_preset=assembly_preset,
            seed=rebuild_seed,
            void_cells=void_cells,
            debug=runtime.debug,
            rift_instance_id=runtime.rift_instance_id,
        )
        updated = updated.model_copy(update={"dev_character_snapshot": self.resources.load_dev_character_snapshot()})
        await self.runtime.save_instance(updated)
        session = await self._reset_dev_run_session(updated)
        return build_rift_screen(self._runtime_for_session(updated, session))

    def _dev_session_id(self, rift_instance_id: str) -> str:
        return f"dev:{rift_instance_id}:run"

    async def _ensure_dev_run_session(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        session_id = self._dev_session_id(runtime.rift_instance_id)
        existing = await self.runtime.get_run_session(session_id)
        if existing is not None:
            return existing
        return await self._reset_dev_run_session(runtime)

    async def _reset_dev_run_session(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        payload = self._session_payload_from_runtime(runtime, previous_session=None)
        session = await self.runtime.create_run_session(payload)
        await self.runtime.enter_node_presence(runtime.rift_instance_id, runtime.current_node_id, _DEV_PARTICIPANT_REF)
        return session

    def _runtime_for_session(self, instance: RiftZoneRuntimeDTO, session: dict[str, Any]) -> RiftZoneRuntimeDTO:
        return instance.model_copy(
            update={
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

    async def _save_runtime_update(
        self,
        *,
        instance: RiftZoneRuntimeDTO,
        previous_session: dict[str, Any],
        updated: RiftZoneRuntimeDTO,
    ) -> None:
        await self.runtime.save_instance(self._instance_runtime_after_update(instance, updated))
        next_session = self._session_payload_from_runtime(updated, previous_session=previous_session)
        await self.runtime.save_run_session(next_session)
        previous_node_id = previous_session.get("current_node_id")
        current_node_id = next_session.get("current_node_id")
        if current_node_id and current_node_id != previous_node_id:
            await self.runtime.move_presence(
                updated.rift_instance_id,
                from_node_id=previous_node_id,
                to_node_id=str(current_node_id),
                participant_ref=_DEV_PARTICIPANT_REF,
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
        previous_session: dict[str, Any] | None,
    ) -> dict[str, Any]:
        existing = dict(previous_session or {})
        return {
            **existing,
            "rift_session_id": existing.get("rift_session_id") or self._dev_session_id(runtime.rift_instance_id),
            "owner_type": existing.get("owner_type") or _DEV_OWNER_TYPE,
            "owner_id": existing.get("owner_id") or _DEV_OWNER_ID,
            "participant_scope": existing.get("participant_scope") or _DEV_OWNER_TYPE,
            "participant_ref": existing.get("participant_ref") or _DEV_PARTICIPANT_REF,
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
