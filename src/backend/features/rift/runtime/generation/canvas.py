from __future__ import annotations

import random
from typing import Any

from src.backend.features.rift.dto import RiftZoneCellDTO
from src.backend.features.rift.dto.runtime import coord_key
from src.backend.features.rift.dto.screen import RiftCoordinateDTO


class CanvasBuilder:
    """Builds and resolves the coordinate canvas before node-pool placement."""

    def grid(self, assembly_preset: dict[str, Any]) -> dict[str, int]:
        grid = dict(assembly_preset.get("geometry") or {})
        return {"width": int(grid.get("width") or 5), "height": int(grid.get("height") or 5)}

    def build_cells(self, *, zone_key: str, width: int, height: int) -> dict[str, RiftZoneCellDTO]:
        cells: dict[str, RiftZoneCellDTO] = {}
        for y in range(height):
            for x in range(width):
                cell_id = f"{zone_key}:{x}_{y}"
                cells[cell_id] = RiftZoneCellDTO(
                    node_id=cell_id,
                    x=x,
                    y=y,
                    pool_node_id="",
                    node_hex="",
                    title="",
                    description="",
                )
        return cells

    def select_node_from_anchor_rules(
        self,
        cells_by_coord: dict[str, str],
        *,
        raw_anchor_rules: Any,
        width: int,
        height: int,
        fallback: RiftCoordinateDTO,
        rng: random.Random,
    ) -> str:
        rules = raw_anchor_rules if isinstance(raw_anchor_rules, list) else [raw_anchor_rules]
        for rule in rules:
            candidates = _anchor_candidates(rule, width=width, height=height)
            if candidates:
                rng.shuffle(candidates)
            for candidate in candidates:
                node_id = cells_by_coord.get(coord_key(candidate.x, candidate.y))
                if node_id:
                    return node_id
        fallback_node_id = cells_by_coord.get(coord_key(fallback.x, fallback.y))
        if fallback_node_id is None:
            raise ValueError("Rift canvas does not contain a usable start/finish coordinate")
        return fallback_node_id

    def resolve_void_cells(
        self,
        *,
        assembly_preset: dict[str, Any],
        requested_void_cells: int | None,
        node_count: int,
    ) -> int:
        if requested_void_cells is not None:
            return requested_void_cells
        active_nodes = dict(assembly_preset.get("active_nodes") or {})
        if active_nodes.get("target") is not None:
            return max(0, node_count - int(active_nodes["target"]))
        policy = dict(assembly_preset.get("blocker_policy") or {})
        if policy.get("hard_void_count") is not None:
            return int(policy["hard_void_count"])
        ratio = float(policy.get("hard_void_ratio") or 0)
        max_count = policy.get("max_hard_void_count")
        max_ratio = policy.get("max_hard_void_ratio")
        resolved = round(node_count * ratio)
        if max_ratio is not None:
            resolved = min(resolved, round(node_count * float(max_ratio)))
        if max_count is not None:
            resolved = min(resolved, int(max_count))
        return max(0, resolved)


def _anchor_candidates(raw_rule: Any, *, width: int, height: int) -> list[RiftCoordinateDTO]:
    if isinstance(raw_rule, dict):
        return [RiftCoordinateDTO(x=int(raw_rule.get("x", 0)), y=int(raw_rule.get("y", 0)))]
    if not isinstance(raw_rule, str):
        return []
    middle_x = width // 2
    middle_y = height // 2
    if raw_rule == "center":
        return [RiftCoordinateDTO(x=middle_x, y=middle_y)]
    if raw_rule == "west_middle":
        return [RiftCoordinateDTO(x=0, y=middle_y)]
    if raw_rule == "east_middle":
        return [RiftCoordinateDTO(x=width - 1, y=middle_y)]
    if raw_rule == "north_west":
        return [RiftCoordinateDTO(x=0, y=0)]
    if raw_rule == "south_east":
        return [RiftCoordinateDTO(x=width - 1, y=height - 1)]
    if raw_rule == "north_edge":
        return [RiftCoordinateDTO(x=x, y=0) for x in range(width)]
    if raw_rule == "south_edge":
        return [RiftCoordinateDTO(x=x, y=height - 1) for x in range(width)]
    if raw_rule == "deep_half":
        return [RiftCoordinateDTO(x=x, y=y) for y in range(height) for x in range(width // 2, width)]
    if raw_rule == "south_half":
        return [RiftCoordinateDTO(x=x, y=y) for y in range(height // 2, height) for x in range(width)]
    return []
