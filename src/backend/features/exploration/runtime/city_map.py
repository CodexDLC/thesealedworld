from __future__ import annotations

from typing import Any

from src.backend.features.world.resources.static.d4_city_map import d4_city_service_markers_for_world


def build_city_map_payload(loc_id: str, loc_data: dict[str, Any]) -> dict[str, Any]:
    flags = _safe_dict(loc_data.get("flags"))
    node_map = _safe_dict(flags.get("city_map"))
    district = _safe_dict(node_map.get("district"))
    if not node_map:
        return {}

    tile_url = str(node_map.get("tile_url") or "")
    if "/" not in tile_url:
        return {}

    size = 7
    grid_size = _safe_int(node_map.get("grid_size"), default=17)
    current_visual_x = _safe_int(node_map.get("visual_x"), default=grid_size // 2)
    current_visual_y = _safe_int(node_map.get("visual_y"), default=grid_size // 2)
    start_visual_x = _clamp(current_visual_x - size // 2, 0, max(0, grid_size - size))
    start_visual_y = _clamp(current_visual_y - size // 2, 0, max(0, grid_size - size))
    tile_base_url = tile_url.rsplit("/", 1)[0]
    playable_bounds = _safe_dict(node_map.get("playable_bounds"))
    world_min_x = _safe_int(playable_bounds.get("min_x"), default=0)
    world_min_y = _safe_int(playable_bounds.get("min_y"), default=0)

    rows = []
    for row_index in range(size):
        row = []
        visual_y = start_visual_y + row_index
        for col_index in range(size):
            visual_x = start_visual_x + col_index
            world_x = world_min_x + visual_x - 1
            world_y = world_min_y + visual_y - 1
            service_markers = d4_city_service_markers_for_world(world_x, world_y)
            row.append(
                {
                    "tile_url": f"{tile_base_url}/d4_{visual_x:02d}_{visual_y:02d}.webp",
                    "visual_x": visual_x,
                    "visual_y": visual_y,
                    "world_x": world_x,
                    "world_y": world_y,
                    "local_x": col_index,
                    "local_y": row_index,
                    "is_current": visual_x == current_visual_x and visual_y == current_visual_y,
                    "service_markers": service_markers,
                }
            )
        rows.append(row)

    return {
        "mode": "viewport_7x7",
        "region_id": node_map.get("region_id") or "",
        "source_region_id": node_map.get("source_region_id") or "",
        "loc_id": loc_id,
        "district": district,
        "size": size,
        "viewport": {
            "visual_x": start_visual_x,
            "visual_y": start_visual_y,
            "max_visual_x": start_visual_x + size - 1,
            "max_visual_y": start_visual_y + size - 1,
        },
        "tile_size": _safe_int(node_map.get("tile_size"), default=256),
        "rows": rows,
        "current": {
            "visual_x": current_visual_x,
            "visual_y": current_visual_y,
            "local_x": _safe_int(district.get("local_x"), default=0),
            "local_y": _safe_int(district.get("local_y"), default=0),
        },
    }


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
