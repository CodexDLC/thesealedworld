from __future__ import annotations

import random
from typing import Any

from src.backend.features.rift.dto import RiftPoolNodeDTO, RiftZoneCellDTO, RiftZonePlacementDTO


class NodePlacementService:
    """Places reusable node-pool records into active canvas cells."""

    def build_placements(
        self,
        *,
        pool_nodes: dict[str, RiftPoolNodeDTO],
        canvas_cells: dict[str, RiftZoneCellDTO],
        active_node_ids: set[str],
        seed: str,
        selection_policy: dict[str, Any],
        reserved_pool_node_ids: dict[str, str] | None = None,
    ) -> tuple[list[RiftZonePlacementDTO], dict[str, RiftZoneCellDTO]]:
        active_canvas_cells = [
            canvas_cells[node_id]
            for node_id in sorted(active_node_ids, key=lambda item: (canvas_cells[item].y, canvas_cells[item].x))
        ]
        required_count = len(active_canvas_cells)
        reserved_pool_node_ids = {
            str(cell_id): str(pool_node_id)
            for cell_id, pool_node_id in dict(reserved_pool_node_ids or {}).items()
            if cell_id in active_node_ids and pool_node_id in pool_nodes
        }
        reserved_cell_ids = set(reserved_pool_node_ids)
        reserved_pool_ids = set(reserved_pool_node_ids.values())
        selected = [
            node
            for node in sorted(pool_nodes.values(), key=lambda node: (node.pool_order, node.pool_node_id))
            if node.pool_node_id not in reserved_pool_ids
        ]
        if selection_policy.get("selection_mode") == "stable_shuffle":
            canvas_signature = ":".join(
                node.node_id for node in active_canvas_cells if node.node_id not in reserved_cell_ids
            )
            rng = random.Random(f"{seed}:node-selection:{canvas_signature}")
            rng.shuffle(selected)
        selected = selected[: required_count - len(reserved_cell_ids)]
        if len(selected) + len(reserved_cell_ids) < required_count:
            raise ValueError(f"Rift node pool needs {required_count} nodes, got {len(selected)}")

        placements: list[RiftZonePlacementDTO] = []
        cells: dict[str, RiftZoneCellDTO] = {}
        selected_index = 0
        for canvas_cell in active_canvas_cells:
            reserved_pool_node_id = reserved_pool_node_ids.get(canvas_cell.node_id)
            if reserved_pool_node_id:
                pool_node = pool_nodes[reserved_pool_node_id]
            else:
                pool_node = selected[selected_index]
                selected_index += 1
            placements.append(
                RiftZonePlacementDTO(
                    cell_id=canvas_cell.node_id,
                    x=canvas_cell.x,
                    y=canvas_cell.y,
                    pool_node_id=pool_node.pool_node_id,
                )
            )
            text = pool_node.generated_text
            cells[canvas_cell.node_id] = RiftZoneCellDTO(
                node_id=canvas_cell.node_id,
                x=canvas_cell.x,
                y=canvas_cell.y,
                pool_node_id=pool_node.pool_node_id,
                node_hex=pool_node.node_hex,
                title=text.title,
                description=text.description,
                approach_view=text.approach_view,
                transition_text=text.transition_text,
                role_fit=pool_node.role_fit,
                tags=pool_node.tags,
            )
        return placements, cells
