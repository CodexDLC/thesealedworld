from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.world.runtime.config import REGION_ROWS, REGION_SIZE, ZONE_SIZE
from src.backend.features.world.runtime.profiles import NAVIGATION_PROFILES, NavigationProfile
from src.backend.features.world.runtime.theme import WorldThemeService
from src.backend.features.world.runtime.threat import ThreatService
from src.backend.features.world.services.navigation_service import WorldNavigationService

if TYPE_CHECKING:
    from src.backend.features.world.integrations.world_data import WorldZoneSeed


@dataclass(frozen=True, slots=True)
class RegionNodeGenerationInput:
    region_id: str
    biome_id: str
    region_archetype: str
    navigation_profile_id: str
    tier_min: int
    tier_max: int
    region_tags: list[str]
    zones: dict[str, WorldZoneSeed]


@dataclass(frozen=True, slots=True)
class RegionBoundaryExit:
    direction: str
    coord: tuple[int, int]
    kind: str


@dataclass(frozen=True, slots=True)
class RegionRoutePlan:
    poi: tuple[int, int]
    exits: tuple[RegionBoundaryExit, ...]


class WorldRegionNodeGenerator:
    """Builds passable node graphs for non-D4 regions from navigation profiles."""

    def build_nodes(self, request: RegionNodeGenerationInput) -> list[dict[str, Any]]:
        profile = NAVIGATION_PROFILES[request.navigation_profile_id]
        min_x, min_y = region_origin(request.region_id)
        coords = [(min_x + local_x, min_y + local_y) for local_y in range(REGION_SIZE) for local_x in range(REGION_SIZE)]
        road_cells: set[tuple[int, int]] = set()
        route_plan = build_region_route_plan(request.region_id)
        open_edges = self._build_connected_edges(request.region_id, coords, road_cells, profile, route_plan)
        nodes = []
        for x, y in coords:
            local_x = x - min_x
            local_y = y - min_y
            zone_id = f"{request.region_id}_{local_x // ZONE_SIZE}_{local_y // ZONE_SIZE}"
            zone = request.zones[zone_id]
            has_road = (x, y) in road_cells
            boundary_exit = self._boundary_exit((x, y), route_plan)
            node_type = self._node_type(
                local_x=local_x,
                local_y=local_y,
                has_road=has_road,
                zone=zone,
                is_poi=(x, y) == route_plan.poi,
                boundary_exit=boundary_exit,
            )
            blocked_exits = self._blocked_exits((x, y), open_edges)
            movement_profile = {
                "navigation_profile_id": profile.id,
                "zone_archetype": zone.zone_archetype,
                "node_type": node_type,
                "is_passable": True,
                "has_road": has_road,
                "travel_cost": self._travel_cost(profile, has_road=has_road),
                "blocked_exits": blocked_exits,
                "gated_exits": self._gated_exits(boundary_exit),
                "route": self._route_profile(has_road=has_road, region_id=request.region_id),
            }
            influence = ThreatService.describe(x, y)
            node_tags = self._node_tags(request, zone, node_type=node_type, has_road=has_road)
            nodes.append(
                {
                    "x": x,
                    "y": y,
                    "zone_id": zone_id,
                    "biome_id": request.biome_id,
                    "node_type": node_type,
                    "terrain_type": self._terrain_type(request.biome_id, node_type),
                    "navigation_profile_id": profile.id,
                    "buildable_kind": None,
                    "landmark_profile": zone.landmark_profile if node_type == "landmark" else None,
                    "movement_profile": movement_profile,
                    "background_key": None,
                    "background_pool_key": request.biome_id,
                    "visual_overrides": {},
                    "services": [],
                    "content": {
                        "title": self._title(request.biome_id, node_type),
                        "description": self._description(request.biome_id, node_type),
                        "environment_tags": node_tags,
                    },
                    "is_active": True,
                    "flags": {
                        "is_active": True,
                        "is_passable": True,
                        "threat_tier": self._node_tier(zone, request),
                        "context_tags": node_tags,
                        "route_plan": {
                            "is_poi": (x, y) == route_plan.poi,
                            "boundary_exit": self._boundary_exit_payload(boundary_exit),
                        },
                        "anchor_influence": {
                            "threat": influence.threat,
                            "tier": influence.tier,
                            "dominant_anchor": influence.dominant_anchor,
                            "tags": influence.tags,
                            "is_inside_city_shield": influence.is_inside_city_shield,
                        },
                        "world_theme": WorldThemeService.build(x, y, loc_id=f"{x}_{y}").model_dump(mode="json"),
                    },
                }
            )
        return nodes

    def _build_connected_edges(
        self,
        region_id: str,
        coords: list[tuple[int, int]],
        road_cells: set[tuple[int, int]],
        profile: NavigationProfile,
        route_plan: RegionRoutePlan,
    ) -> set[frozenset[tuple[int, int]]]:
        coord_set = set(coords)
        rng = random.Random(f"{region_id}:{profile.id}:node_graph:v1")
        start = min(coords, key=lambda coord: abs(coord[0] - average_x(coords)) + abs(coord[1] - average_y(coords)))
        visited = {start}
        stack = [start]
        edges: set[frozenset[tuple[int, int]]] = set()
        degree: dict[tuple[int, int], int] = {coord: 0 for coord in coords}

        for route_exit in route_plan.exits:
            self._open_path(edges, degree, route_exit.coord, route_plan.poi, coord_set)

        while stack:
            current = stack[-1]
            neighbors = [neighbor for neighbor in self._neighbors(current, coord_set) if neighbor not in visited]
            rng.shuffle(neighbors)
            if not neighbors:
                stack.pop()
                continue
            neighbor = neighbors[0]
            self._open_edge(edges, degree, current, neighbor)
            visited.add(neighbor)
            stack.append(neighbor)

        candidates = [
            (coord, neighbor)
            for coord in coords
            for neighbor in self._neighbors(coord, coord_set)
            if coord < neighbor and frozenset((coord, neighbor)) not in edges
        ]
        rng.shuffle(candidates)
        for coord, neighbor in candidates:
            cap = profile.road_degree if coord in road_cells and neighbor in road_cells else profile.max_degree
            if not self._can_open(degree, coord, neighbor, cap):
                continue
            if degree[coord] < profile.target_degree or degree[neighbor] < profile.target_degree:
                self._open_edge(edges, degree, coord, neighbor)
                continue
            if rng.random() < profile.loop_chance:
                self._open_edge(edges, degree, coord, neighbor)

        return edges

    def _open_path(
        self,
        edges: set[frozenset[tuple[int, int]]],
        degree: dict[tuple[int, int], int],
        start: tuple[int, int],
        end: tuple[int, int],
        coord_set: set[tuple[int, int]],
    ) -> None:
        current = start
        while current != end:
            next_coord = self._next_path_step(current, end)
            if next_coord not in coord_set:
                break
            self._open_edge(edges, degree, current, next_coord)
            current = next_coord

    @staticmethod
    def _next_path_step(current: tuple[int, int], end: tuple[int, int]) -> tuple[int, int]:
        x, y = current
        end_x, end_y = end
        if x != end_x:
            return (x + (1 if end_x > x else -1), y)
        if y != end_y:
            return (x, y + (1 if end_y > y else -1))
        return current

    @staticmethod
    def _neighbors(coord: tuple[int, int], coord_set: set[tuple[int, int]]) -> list[tuple[int, int]]:
        x, y = coord
        result = []
        for dx, dy in WorldNavigationService.DIRECTIONS.values():
            neighbor = (x + dx, y + dy)
            if neighbor in coord_set:
                result.append(neighbor)
        return result

    @staticmethod
    def _can_open(
        degree: dict[tuple[int, int], int],
        coord: tuple[int, int],
        neighbor: tuple[int, int],
        cap: int,
    ) -> bool:
        return degree[coord] < cap and degree[neighbor] < cap

    @staticmethod
    def _open_edge(
        edges: set[frozenset[tuple[int, int]]],
        degree: dict[tuple[int, int], int],
        coord: tuple[int, int],
        neighbor: tuple[int, int],
    ) -> None:
        edge = frozenset((coord, neighbor))
        if edge in edges:
            return
        edges.add(edge)
        degree[coord] += 1
        degree[neighbor] += 1

    @staticmethod
    def _blocked_exits(
        coord: tuple[int, int],
        open_edges: set[frozenset[tuple[int, int]]],
    ) -> list[str]:
        x, y = coord
        blocked = []
        for direction, (dx, dy) in WorldNavigationService.DIRECTIONS.items():
            neighbor = (x + dx, y + dy)
            if frozenset((coord, neighbor)) not in open_edges:
                blocked.append(direction)
        return blocked

    @staticmethod
    def _node_type(
        *,
        local_x: int,
        local_y: int,
        has_road: bool,
        zone: WorldZoneSeed,
        is_poi: bool,
        boundary_exit: RegionBoundaryExit | None,
    ) -> str:
        if boundary_exit is not None:
            return "region_exit"
        if is_poi:
            return "landmark"
        if has_road:
            return "regional_road"
        if local_x in (0, REGION_SIZE - 1) or local_y in (0, REGION_SIZE - 1):
            return "region_edge"
        return zone.zone_archetype

    @staticmethod
    def _travel_cost(profile: NavigationProfile, *, has_road: bool) -> float:
        if has_road:
            return 1.0
        if profile.id == "mountain_passes":
            return 1.5
        if profile.id == "swamp_channels":
            return 1.4
        if profile.id == "forest_paths":
            return 1.2
        return 1.25

    @staticmethod
    def _route_profile(*, has_road: bool, region_id: str) -> dict[str, Any]:
        if not has_road:
            return {}
        return {
            "type": "regional_route",
            "role": "region_crossroad",
            "region_id": region_id,
            "tags": ["road", "regional_route", "crossroad"],
        }

    @staticmethod
    def _boundary_exit(coord: tuple[int, int], route_plan: RegionRoutePlan) -> RegionBoundaryExit | None:
        for route_exit in route_plan.exits:
            if route_exit.coord == coord:
                return route_exit
        return None

    @staticmethod
    def _gated_exits(boundary_exit: RegionBoundaryExit | None) -> dict[str, Any]:
        if boundary_exit is None:
            return {}
        return {
            boundary_exit.direction: {
                "kind": boundary_exit.kind,
                "state": "locked",
                "unlock_condition": "region_route_unlock",
                "tags": ["region_exit", boundary_exit.kind],
            }
        }

    @staticmethod
    def _boundary_exit_payload(boundary_exit: RegionBoundaryExit | None) -> dict[str, Any] | None:
        if boundary_exit is None:
            return None
        return {
            "direction": boundary_exit.direction,
            "coord": [boundary_exit.coord[0], boundary_exit.coord[1]],
            "kind": boundary_exit.kind,
        }

    @staticmethod
    def _node_tier(zone: WorldZoneSeed, request: RegionNodeGenerationInput) -> int:
        return max(request.tier_min, min(request.tier_max, zone.tier))

    @staticmethod
    def _node_tags(
        request: RegionNodeGenerationInput,
        zone: WorldZoneSeed,
        *,
        node_type: str,
        has_road: bool,
    ) -> list[str]:
        tags = [request.biome_id, request.region_archetype, zone.zone_archetype, node_type, *request.region_tags]
        tags.extend(zone.population_tags)
        if has_road:
            tags.extend(["road", "regional_route"])
        return list(dict.fromkeys(str(tag) for tag in tags if tag))

    @staticmethod
    def _terrain_type(biome_id: str, node_type: str) -> str:
        if node_type == "regional_road":
            return f"{biome_id}_trail"
        if node_type == "landmark":
            return f"{biome_id}_landmark"
        return biome_id

    @staticmethod
    def _title(biome_id: str, node_type: str) -> str:
        return f"{biome_id}:{node_type}"

    @staticmethod
    def _description(biome_id: str, node_type: str) -> str:
        return f"Generated {node_type} node in {biome_id} region."


def region_origin(region_id: str) -> tuple[int, int]:
    row = REGION_ROWS.index(region_id[0])
    col = int(region_id[1:]) - 1
    return col * REGION_SIZE, row * REGION_SIZE


def build_region_route_plan(region_id: str) -> RegionRoutePlan:
    min_x, min_y = region_origin(region_id)
    poi = (min_x + REGION_SIZE // 2, min_y + REGION_SIZE // 2)
    exits = _first_ring_gate_region_exits(region_id, min_x=min_x, min_y=min_y)
    if exits:
        return RegionRoutePlan(poi=poi, exits=tuple(exits))
    return RegionRoutePlan(
        poi=poi,
        exits=(
            RegionBoundaryExit("north", (min_x + 7, min_y), "wild_region_exit"),
            RegionBoundaryExit("south", (min_x + 7, min_y + REGION_SIZE - 1), "wild_region_exit"),
        ),
    )


def _first_ring_gate_region_exits(region_id: str, *, min_x: int, min_y: int) -> list[RegionBoundaryExit]:
    mid_x = min_x + REGION_SIZE // 2
    mid_y = min_y + REGION_SIZE // 2
    max_x = min_x + REGION_SIZE - 1
    max_y = min_y + REGION_SIZE - 1
    if region_id == "C4":
        return [
            RegionBoundaryExit("south", (mid_x, max_y), "city_gate_approach"),
            RegionBoundaryExit("west", (min_x, mid_y - 2), "first_ring_route"),
            RegionBoundaryExit("east", (max_x, mid_y + 2), "first_ring_route"),
        ]
    if region_id == "E4":
        return [
            RegionBoundaryExit("north", (mid_x, min_y), "city_gate_approach"),
            RegionBoundaryExit("west", (min_x, mid_y + 2), "first_ring_route"),
            RegionBoundaryExit("east", (max_x, mid_y - 2), "first_ring_route"),
        ]
    if region_id == "D3":
        return [
            RegionBoundaryExit("east", (max_x, mid_y), "city_gate_approach"),
            RegionBoundaryExit("north", (mid_x - 2, min_y), "first_ring_route"),
            RegionBoundaryExit("south", (mid_x + 2, max_y), "first_ring_route"),
        ]
    if region_id == "D5":
        return [
            RegionBoundaryExit("west", (min_x, mid_y), "city_gate_approach"),
            RegionBoundaryExit("north", (mid_x + 2, min_y), "first_ring_route"),
            RegionBoundaryExit("south", (mid_x - 2, max_y), "first_ring_route"),
        ]
    return []


def average_x(coords: list[tuple[int, int]]) -> float:
    return sum(coord[0] for coord in coords) / len(coords)


def average_y(coords: list[tuple[int, int]]) -> float:
    return sum(coord[1] for coord in coords) / len(coords)
