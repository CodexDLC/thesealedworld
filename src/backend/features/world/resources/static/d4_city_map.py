from __future__ import annotations

from typing import Any

from src.backend.features.world.runtime.config import REGION_ROWS, REGION_SIZE, ZONE_SIZE

D4_CITY_MAP_REGION_ID = "D4_CITY"
D4_CITY_SOURCE_REGION_ID = "D4"
D4_CITY_VISUAL_GRID_SIZE = REGION_SIZE + 2
D4_CITY_TILE_SIZE = 256
D4_CITY_MAP_VERSION = "v1"
D4_CITY_TILE_FORMAT = "webp"
D4_CITY_TILE_BASE_URL = f"/static/images/exploration/city/d4/map/{D4_CITY_MAP_VERSION}/tiles_17x17_256"
D4_CITY_SERVICE_MARKER_CORNERS = {"top-left", "top-right", "bottom-left", "bottom-right"}
D4_CITY_SERVICE_MARKERS: dict[tuple[int, int], tuple[dict[str, str], ...]] = {
    (51, 51): (
        {
            "service_id": "svc_arena_main",
            "service_type": "arena",
            "label": "Арена",
            "icon_url": "/static/images/ui/service-icons/arena.svg",
            "corner": "top-left",
        },
    ),
    (53, 51): (
        {
            "service_id": "svc_market_hub",
            "service_type": "market",
            "label": "Торговый зал",
            "icon_url": "/static/images/ui/service-icons/market.svg",
            "corner": "top-left",
        },
    ),
    (51, 53): (
        {
            "service_id": "svc_town_hall_hub",
            "service_type": "town_hall",
            "label": "Реестр",
            "icon_url": "/static/images/ui/service-icons/default.svg",
            "corner": "top-left",
        },
    ),
    (53, 53): (
        {
            "service_id": "svc_tavern_hub",
            "service_type": "tavern",
            "label": "Постоялый двор",
            "icon_url": "/static/images/ui/service-icons/tavern.svg",
            "corner": "top-right",
        },
    ),
    (50, 54): (
        {
            "service_id": "svc_blacksmith_repair",
            "service_type": "workshop.blacksmith",
            "label": "Ремесленный двор",
            "icon_url": "/static/images/ui/service-icons/blacksmith.svg",
            "corner": "top-right",
        },
    ),
}

D4_CITY_PLAYABLE_MIN_X = (4 - 1) * REGION_SIZE
D4_CITY_PLAYABLE_MIN_Y = REGION_ROWS.index("D") * REGION_SIZE
D4_CITY_PLAYABLE_MAX_X = D4_CITY_PLAYABLE_MIN_X + REGION_SIZE - 1
D4_CITY_PLAYABLE_MAX_Y = D4_CITY_PLAYABLE_MIN_Y + REGION_SIZE - 1
D4_CITY_VISUAL_MIN_X = D4_CITY_PLAYABLE_MIN_X - 1
D4_CITY_VISUAL_MIN_Y = D4_CITY_PLAYABLE_MIN_Y - 1
D4_CITY_VISUAL_MAX_X = D4_CITY_PLAYABLE_MAX_X + 1
D4_CITY_VISUAL_MAX_Y = D4_CITY_PLAYABLE_MAX_Y + 1


def d4_city_tile_url(local_x: int, local_y: int) -> str:
    """Return the frontend URL for a D4 visual-map tile."""

    if not 0 <= local_x < D4_CITY_VISUAL_GRID_SIZE or not 0 <= local_y < D4_CITY_VISUAL_GRID_SIZE:
        raise ValueError(f"D4 city visual tile is out of range: {local_x},{local_y}")
    return f"{D4_CITY_TILE_BASE_URL}/d4_{local_x:02d}_{local_y:02d}.{D4_CITY_TILE_FORMAT}"


def d4_city_global_to_visual(x: int, y: int) -> tuple[int, int]:
    return x - D4_CITY_VISUAL_MIN_X, y - D4_CITY_VISUAL_MIN_Y


def is_d4_city_visual_coord(x: int, y: int) -> bool:
    return D4_CITY_VISUAL_MIN_X <= x <= D4_CITY_VISUAL_MAX_X and D4_CITY_VISUAL_MIN_Y <= y <= D4_CITY_VISUAL_MAX_Y


def is_d4_city_playable_coord(x: int, y: int) -> bool:
    return (
        D4_CITY_PLAYABLE_MIN_X <= x <= D4_CITY_PLAYABLE_MAX_X and D4_CITY_PLAYABLE_MIN_Y <= y <= D4_CITY_PLAYABLE_MAX_Y
    )


def d4_city_service_markers_for_world(x: int, y: int) -> list[dict[str, str]]:
    markers = D4_CITY_SERVICE_MARKERS.get((x, y), ())
    return [_normalize_service_marker(marker) for marker in markers]


def _normalize_service_marker(marker: dict[str, str]) -> dict[str, str]:
    payload = dict(marker)
    if payload.get("corner") not in D4_CITY_SERVICE_MARKER_CORNERS:
        payload["corner"] = "bottom-right"
    return payload


def build_d4_city_map_node_metadata(x: int, y: int) -> dict[str, Any]:
    """Build map metadata for both playable city nodes and non-playable wall-contour tiles."""

    if not is_d4_city_visual_coord(x, y):
        raise ValueError(f"Coordinate is outside D4 city visual map: {x},{y}")

    visual_x, visual_y = d4_city_global_to_visual(x, y)
    is_playable = is_d4_city_playable_coord(x, y)
    metadata: dict[str, Any] = {
        "region_id": D4_CITY_MAP_REGION_ID,
        "source_region_id": D4_CITY_SOURCE_REGION_ID,
        "grid_size": D4_CITY_VISUAL_GRID_SIZE,
        "tile_size": D4_CITY_TILE_SIZE,
        "tile_url": d4_city_tile_url(visual_x, visual_y),
        "visual_x": visual_x,
        "visual_y": visual_y,
        "world_x": x,
        "world_y": y,
        "is_playable": is_playable,
        "is_visual_contour": not is_playable,
        "wall_blocks_city_crossing": not is_playable,
        "playable_bounds": {
            "min_x": D4_CITY_PLAYABLE_MIN_X,
            "min_y": D4_CITY_PLAYABLE_MIN_Y,
            "max_x": D4_CITY_PLAYABLE_MAX_X,
            "max_y": D4_CITY_PLAYABLE_MAX_Y,
            "min_visual_x": 1,
            "min_visual_y": 1,
            "max_visual_x": D4_CITY_VISUAL_GRID_SIZE - 2,
            "max_visual_y": D4_CITY_VISUAL_GRID_SIZE - 2,
        },
    }
    if is_playable:
        city_x = visual_x - 1
        city_y = visual_y - 1
        district_x = city_x // ZONE_SIZE
        district_y = city_y // ZONE_SIZE
        metadata["district"] = {
            "key": f"{D4_CITY_MAP_REGION_ID}_{district_x}_{district_y}",
            "x": district_x,
            "y": district_y,
            "local_x": city_x % ZONE_SIZE,
            "local_y": city_y % ZONE_SIZE,
            "size": ZONE_SIZE,
        }
    else:
        metadata["district"] = None
    return metadata


def build_d4_city_map_tile_manifest() -> list[dict[str, Any]]:
    return [
        build_d4_city_map_node_metadata(x, y)
        for y in range(D4_CITY_VISUAL_MIN_Y, D4_CITY_VISUAL_MAX_Y + 1)
        for x in range(D4_CITY_VISUAL_MIN_X, D4_CITY_VISUAL_MAX_X + 1)
    ]
