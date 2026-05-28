from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.backend.features.rift.runtime.generation.events import NodeEventSeeder

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftPoolNodeDTO, RiftZoneRuntimeDTO


class ZoneChainBuilder:
    """Builds prepared multi-zone rift chains from the same zone assembly preset."""

    def build(
        self,
        *,
        setting: dict[str, Any],
        pool_nodes: dict[str, RiftPoolNodeDTO],
        scale_preset: dict[str, Any],
        assembly_preset: dict[str, Any],
        seed: str | None = None,
        void_cells: int | None = None,
        debug: bool = True,
        rift_instance_id: str | None = None,
    ) -> RiftZoneRuntimeDTO:
        from src.backend.features.rift.runtime.generation.zone_instance import build_zone_runtime

        _ = void_cells
        chain_policy = dict(assembly_preset.get("zone_chain") or {})
        level_count = int(chain_policy.get("levels") or 1)
        if level_count <= 1:
            return build_zone_runtime(
                setting=setting,
                pool_nodes=pool_nodes,
                scale_preset=scale_preset,
                assembly_preset=assembly_preset,
                seed=seed,
                debug=debug,
                rift_instance_id=rift_instance_id,
            )
        active_target = int(dict(assembly_preset.get("active_nodes") or {}).get("target") or 0)
        if active_target <= 0:
            raise ValueError("Rift zone chain requires active_nodes.target")
        sorted_pool_nodes = sorted(pool_nodes.values(), key=lambda node: (node.pool_order, node.pool_node_id))
        required_pool_count = level_count * active_target
        if len(sorted_pool_nodes) < required_pool_count:
            raise ValueError(f"Rift zone chain needs {required_pool_count} pool nodes, got {len(sorted_pool_nodes)}")

        resolved_seed = seed or str(dict(setting.get("assembly_options") or {}).get("default_seed") or "rift-dev")
        instance_id = rift_instance_id or f"dev-rift-{_short_seed(resolved_seed)}-{uuid4().hex[:8]}"
        chain_order = [f"z{index:02}" for index in range(1, level_count + 1)]
        runtimes: dict[str, RiftZoneRuntimeDTO] = {}
        event_seeder = NodeEventSeeder()
        for index, zone_key in enumerate(chain_order, start=1):
            pool_slice = sorted_pool_nodes[(index - 1) * active_target : index * active_target]
            zone_preset = {
                **assembly_preset,
                "zone_key": zone_key,
            }
            runtime = build_zone_runtime(
                setting=setting,
                pool_nodes={node.pool_node_id: node for node in pool_slice},
                scale_preset=scale_preset,
                assembly_preset=zone_preset,
                seed=f"{resolved_seed}:{zone_key}",
                debug=debug,
                rift_instance_id=instance_id,
                current_zone_key=zone_key,
                zone_depth=index,
            )
            if index < level_count:
                runtime = event_seeder.add_next_zone_transition_event(
                    runtime,
                    next_zone_key=chain_order[index],
                    next_zone_depth=index + 1,
                )
            runtimes[zone_key] = runtime

        chain = {
            zone_key: runtime.model_copy(update={"zone_chain": {}}).model_dump(mode="json")
            for zone_key, runtime in runtimes.items()
        }
        first_zone_key = chain_order[0]
        first_runtime = runtimes[first_zone_key]
        return first_runtime.model_copy(
            update={
                "zone_chain_order": chain_order,
                "zone_chain": chain,
            }
        )


def build_zone_chain_runtime(
    *,
    setting: dict[str, Any],
    pool_nodes: dict[str, RiftPoolNodeDTO],
    scale_preset: dict[str, Any],
    assembly_preset: dict[str, Any],
    seed: str | None = None,
    void_cells: int | None = None,
    debug: bool = True,
    rift_instance_id: str | None = None,
) -> RiftZoneRuntimeDTO:
    return ZoneChainBuilder().build(
        setting=setting,
        pool_nodes=pool_nodes,
        scale_preset=scale_preset,
        assembly_preset=assembly_preset,
        seed=seed,
        void_cells=void_cells,
        debug=debug,
        rift_instance_id=rift_instance_id,
    )


def _short_seed(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
