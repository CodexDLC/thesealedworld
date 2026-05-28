from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftPassageEdgeDTO, RiftZoneCellDTO


class PassageGraphBuilder:
    """Builds the playable passage graph over an already prepared canvas."""

    def build_graph_state(
        self,
        *,
        assembly_preset: dict[str, Any],
        nodes: dict[str, RiftZoneCellDTO],
        cells_by_coord: dict[str, str],
        width: int,
        height: int,
        start_node_id: str,
        finish_node_id: str,
        void_cells: int,
        seed: str,
        protected_node_ids: set[str] | None = None,
        required_start_node_ids: set[str] | None = None,
    ) -> tuple[set[str], dict[str, RiftPassageEdgeDTO], str]:
        from src.backend.features.rift.runtime.generation.zone_instance import _build_graph_state

        return _build_graph_state(
            assembly_preset=assembly_preset,
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
            void_cells=void_cells,
            seed=seed,
            protected_node_ids=protected_node_ids,
            required_start_node_ids=required_start_node_ids,
        )
