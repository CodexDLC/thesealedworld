from __future__ import annotations

from typing import Any

from src.backend.features.rift.dto import RiftZoneRuntimeDTO
from src.backend.infrastructure.rift.models import RiftInstanceState, RiftRunState


class RiftInstanceStateMapper:
    def to_model(self, runtime: RiftZoneRuntimeDTO, *, status: str = "active") -> RiftInstanceState:
        return RiftInstanceState(
            rift_instance_id=runtime.rift_instance_id,
            setting_key=str(runtime.setting.get("setting_key") or "unknown"),
            status=status,
            instance_version=int(runtime.setting.get("schema_version") or 1),
            generation_seed=str(dict(runtime.setting.get("assembly_options") or {}).get("default_seed") or ""),
            scale_preset_key=runtime.scale_preset_key,
            assembly_preset_key=runtime.assembly_preset_key,
            zones_json=self._zones_json(runtime),
            graph_json=self._graph_json(runtime),
            nodes_state_json=self._nodes_state_json(runtime),
            objectives_json=self._objectives_json(runtime),
            runtime_flags_json={"flags": sorted(runtime.runtime_flags)},
            state_meta_json=self._state_meta_json(runtime),
        )

    def _zones_json(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        return {
            "zone_instance_id": runtime.zone_instance_id,
            "zone_canvas_key": runtime.zone_canvas_key,
            "current_zone_key": runtime.current_zone_key,
            "zone_depth": runtime.zone_depth,
            "zone_chain_order": runtime.zone_chain_order,
            "zone_chain": runtime.zone_chain,
            "debug_map_width": runtime.debug_map_width,
            "debug_map_height": runtime.debug_map_height,
            "start_node_id": runtime.start_node_id,
            "finish_node_id": runtime.finish_node_id,
            "cells_by_coord": runtime.cells_by_coord,
            "placements": [placement.model_dump(mode="json") for placement in runtime.placements],
            "nodes": {node_id: node.model_dump(mode="json") for node_id, node in runtime.nodes.items()},
        }

    def _graph_json(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        return {
            "passage_edges": {
                edge_key: edge.model_dump(mode="json") for edge_key, edge in runtime.passage_edges.items()
            },
            "void_node_ids": sorted(runtime.void_node_ids),
            "void_coords": [coord.model_dump(mode="json") for coord in runtime.void_coords],
        }

    def _nodes_state_json(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        return {
            "node_events": runtime.node_events,
            "node_states": runtime.node_states,
            "gate_states": runtime.gate_states,
            "heart_state": runtime.heart_state,
        }

    def _objectives_json(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        screen = dict(runtime.setting.get("screen") or {})
        return {
            "objective": dict(screen.get("objective") or {}),
            "finish_node_id": runtime.finish_node_id,
            "heart_state": runtime.heart_state,
        }

    def _state_meta_json(self, runtime: RiftZoneRuntimeDTO) -> dict[str, Any]:
        return {
            "debug": runtime.debug,
            "setting_snapshot": runtime.setting,
            "scale_preset": runtime.scale_preset,
            "assembly_preset": runtime.assembly_preset,
            "population_context": runtime.population_context,
            "dev_character_snapshot": runtime.dev_character_snapshot,
            "cold_restore_policy": {
                "source": "rift_instance_state",
                "current_position_source": "rift_run_state",
            },
        }

    def to_runtime(self, state: RiftInstanceState) -> RiftZoneRuntimeDTO:
        zones = dict(state.zones_json or {})
        graph = dict(state.graph_json or {})
        nodes_state = dict(state.nodes_state_json or {})
        meta = dict(state.state_meta_json or {})
        return RiftZoneRuntimeDTO.model_validate(
            {
                "rift_instance_id": state.rift_instance_id,
                "zone_instance_id": zones.get("zone_instance_id") or state.rift_instance_id,
                "zone_canvas_key": zones.get("zone_canvas_key") or "unknown",
                "scale_preset_key": state.scale_preset_key or "",
                "assembly_preset_key": state.assembly_preset_key or "",
                "setting": dict(meta.get("setting_snapshot") or {}),
                "scale_preset": dict(meta.get("scale_preset") or {}),
                "assembly_preset": dict(meta.get("assembly_preset") or {}),
                "placements": list(zones.get("placements") or []),
                "nodes": dict(zones.get("nodes") or {}),
                "cells_by_coord": dict(zones.get("cells_by_coord") or {}),
                "passage_edges": dict(graph.get("passage_edges") or {}),
                "void_node_ids": set(graph.get("void_node_ids") or []),
                "void_coords": list(graph.get("void_coords") or []),
                "debug_map_width": int(zones.get("debug_map_width") or 5),
                "debug_map_height": int(zones.get("debug_map_height") or 5),
                "start_node_id": str(zones.get("start_node_id") or ""),
                "finish_node_id": str(zones.get("finish_node_id") or ""),
                "current_node_id": str(zones.get("start_node_id") or ""),
                "current_zone_key": str(zones.get("current_zone_key") or "z01"),
                "zone_depth": int(zones.get("zone_depth") or 1),
                "zone_chain_order": list(zones.get("zone_chain_order") or []),
                "zone_chain": dict(zones.get("zone_chain") or {}),
                "visited_node_ids": {str(zones.get("start_node_id") or "")},
                "runtime_flags": set(dict(state.runtime_flags_json or {}).get("flags") or []),
                "node_events": dict(nodes_state.get("node_events") or {}),
                "node_states": dict(nodes_state.get("node_states") or {}),
                "gate_states": dict(nodes_state.get("gate_states") or {}),
                "heart_state": dict(nodes_state.get("heart_state") or {}),
                "population_context": dict(meta.get("population_context") or {}),
                "dev_character_snapshot": dict(meta.get("dev_character_snapshot") or {}),
                "debug": bool(meta.get("debug", False)),
            }
        )


class RiftRunStateMapper:
    def from_session_payload(self, payload: dict[str, Any], *, status: str | None = None) -> RiftRunState:
        rift_run_id = str(payload.get("rift_session_id") or payload.get("rift_run_id") or "")
        if not rift_run_id:
            raise ValueError("Rift run state payload must contain rift_session_id or rift_run_id")
        return RiftRunState(
            rift_run_id=rift_run_id,
            rift_instance_id=str(payload["rift_instance_id"]),
            participant_scope=str(payload.get("participant_scope") or payload.get("owner_type") or "solo"),
            participant_ref=str(payload.get("participant_ref") or payload.get("owner_id") or ""),
            status=status or str(payload.get("status") or "active"),
            current_zone_key=str(payload.get("current_zone_key") or "z01"),
            current_node_id=str(payload["current_node_id"]),
            previous_node_id=payload.get("previous_node_id"),
            heading=payload.get("heading"),
            visited_node_ids=[str(node_id) for node_id in payload.get("visited_node_ids", [])],
            discovered_node_ids=[str(node_id) for node_id in payload.get("discovered_node_ids", [])],
            active_encounter_id=payload.get("active_encounter_id"),
            entry_context_json=dict(payload.get("entry_context") or payload.get("entry_context_json") or {}),
            run_state_json=self._run_state_json(payload),
        )

    def from_runtime(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        rift_run_id: str,
        participant_scope: str,
        participant_ref: str,
        entry_context: dict[str, Any] | None = None,
        status: str = "active",
    ) -> RiftRunState:
        return self.from_session_payload(
            {
                "rift_run_id": rift_run_id,
                "rift_instance_id": runtime.rift_instance_id,
                "participant_scope": participant_scope,
                "participant_ref": participant_ref,
                "status": status,
                "current_zone_key": runtime.current_zone_key,
                "current_node_id": runtime.current_node_id,
                "previous_node_id": runtime.previous_node_id,
                "heading": runtime.heading,
                "visited_node_ids": sorted(runtime.visited_node_ids),
                "discovered_node_ids": sorted(runtime.visited_node_ids),
                "active_encounter_id": None,
                "entry_context": entry_context or {},
                "last_travel": runtime.last_travel,
            }
        )

    def _run_state_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "zone_instance_id": payload.get("zone_instance_id"),
            "last_travel": payload.get("last_travel"),
            "restore_policy": {
                "active_travel": "drop_to_current_node",
            },
        }

    def to_session_payload(self, state: RiftRunState) -> dict[str, Any]:
        run_state = dict(state.run_state_json or {})
        return {
            "rift_session_id": state.rift_run_id,
            "owner_type": state.participant_scope,
            "owner_id": state.participant_ref,
            "participant_scope": state.participant_scope,
            "participant_ref": state.participant_ref,
            "rift_instance_id": state.rift_instance_id,
            "zone_instance_id": run_state.get("zone_instance_id"),
            "current_zone_key": state.current_zone_key,
            "current_node_id": state.current_node_id,
            "previous_node_id": state.previous_node_id,
            "heading": state.heading,
            "visited_node_ids": list(state.visited_node_ids or []),
            "discovered_node_ids": list(state.discovered_node_ids or []),
            "active_travel": None,
            "last_travel": run_state.get("last_travel"),
            "active_encounter_id": state.active_encounter_id,
            "entry_context": dict(state.entry_context_json or {}),
            "status": state.status,
            "is_dirty": False,
            "dirty": {"dirty": False},
        }
