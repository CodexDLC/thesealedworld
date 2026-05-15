from types import SimpleNamespace

import pytest

from src.backend.features.world.integrations.world_data import WorldZoneSeed
from src.backend.features.world.runtime.node_graph import (
    RegionNodeGenerationInput,
    WorldRegionNodeGenerator,
    build_region_route_plan,
)
from src.backend.features.world.services.navigation_service import WorldNavigationService


@pytest.mark.unit
def test_region_node_generator_keeps_external_region_reachable() -> None:
    zones = {
        f"C4_{zx}_{zy}": WorldZoneSeed(
            id=f"C4_{zx}_{zy}",
            region_id="C4",
            biome_id="mountains",
            tier=1,
            zone_archetype="mountains_core" if zx == 1 and zy == 1 else "mountains_edge",
            navigation_profile_id="mountain_passes",
            landmark_profile="frontier_approach",
            population_tags=["first_ring", "north_gate_frontier"],
            flags={},
        )
        for zx in range(3)
        for zy in range(3)
    }
    request = RegionNodeGenerationInput(
        region_id="C4",
        biome_id="mountains",
        region_archetype="first_ring_c4",
        navigation_profile_id="mountain_passes",
        tier_min=1,
        tier_max=3,
        region_tags=["first_ring", "mountains"],
        zones=zones,
    )

    raw_nodes = WorldRegionNodeGenerator().build_nodes(request)
    nodes = {
        f"{raw['x']}_{raw['y']}": SimpleNamespace(
            x=raw["x"],
            y=raw["y"],
            zone_id=raw["zone_id"],
            services=raw["services"],
            content=raw["content"],
            flags=raw["flags"],
            movement_profile=raw["movement_profile"],
            is_active=raw["is_active"],
        )
        for raw in raw_nodes
    }
    navigation = WorldNavigationService()
    visited = {"52_37"}
    queue = ["52_37"]
    while queue:
        current = queue.pop(0)
        for key in navigation.calculate_exits(nodes[current], nodes):
            if not key.startswith("nav:"):
                continue
            target = key.removeprefix("nav:")
            if target not in visited:
                visited.add(target)
                queue.append(target)

    assert len(raw_nodes) == 225
    assert visited == set(nodes)
    assert all(raw["movement_profile"]["is_passable"] is True for raw in raw_nodes)
    assert sum(1 for raw in raw_nodes if raw["movement_profile"]["blocked_exits"]) > 200


@pytest.mark.unit
def test_first_ring_gate_regions_have_three_exits_without_opposite_gate() -> None:
    plans = {region_id: build_region_route_plan(region_id) for region_id in ("C4", "E4", "D3", "D5")}

    assert [route_exit.direction for route_exit in plans["C4"].exits] == ["south", "west", "east"]
    assert [route_exit.direction for route_exit in plans["E4"].exits] == ["north", "west", "east"]
    assert [route_exit.direction for route_exit in plans["D3"].exits] == ["east", "north", "south"]
    assert [route_exit.direction for route_exit in plans["D5"].exits] == ["west", "north", "south"]
    assert "north" not in {route_exit.direction for route_exit in plans["C4"].exits}
    assert "south" not in {route_exit.direction for route_exit in plans["E4"].exits}
    assert "west" not in {route_exit.direction for route_exit in plans["D3"].exits}
    assert "east" not in {route_exit.direction for route_exit in plans["D5"].exits}


@pytest.mark.unit
def test_external_region_generator_marks_route_plan_exits() -> None:
    zones = {
        f"C4_{zx}_{zy}": WorldZoneSeed(
            id=f"C4_{zx}_{zy}",
            region_id="C4",
            biome_id="mountains",
            tier=1,
            zone_archetype="mountains_core" if zx == 1 and zy == 1 else "mountains_edge",
            navigation_profile_id="mountain_passes",
            landmark_profile="frontier_approach",
            population_tags=["first_ring", "north_gate_frontier"],
            flags={},
        )
        for zx in range(3)
        for zy in range(3)
    }
    raw_nodes = WorldRegionNodeGenerator().build_nodes(
        RegionNodeGenerationInput(
            region_id="C4",
            biome_id="mountains",
            region_archetype="first_ring_c4",
            navigation_profile_id="mountain_passes",
            tier_min=1,
            tier_max=3,
            region_tags=["first_ring", "mountains"],
            zones=zones,
        )
    )

    exits = [raw for raw in raw_nodes if raw["node_type"] == "region_exit"]

    assert len(exits) == 3
    assert {raw["flags"]["route_plan"]["boundary_exit"]["direction"] for raw in exits} == {"south", "west", "east"}
    assert all(raw["movement_profile"]["gated_exits"] for raw in exits)
