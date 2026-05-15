from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.disable(logging.CRITICAL)
try:
    from loguru import logger

    logger.remove()
except Exception:
    pass

from src.backend.features.monsters.resources.spawn_config import BIOME_FAMILIES, TIER_AVAILABILITY  # noqa: E402
from src.backend.features.monsters.runtime.hashing import compute_context_hash, normalize_tags  # noqa: E402
from src.backend.features.monsters.services.world_population_service import WorldMonsterPopulationService  # noqa: E402
from src.backend.features.world.integrations.world_data import WorldZoneSeed  # noqa: E402
from src.backend.features.world.runtime.node_graph import (  # noqa: E402
    RegionNodeGenerationInput,
    WorldRegionNodeGenerator,
)
from src.backend.features.world.services.generator_service import D4_RIFT_PROFILES, LLMWorldGenerator  # noqa: E402
from src.backend.features.world.services.navigation_service import WorldNavigationService  # noqa: E402


@dataclass(slots=True)
class MemoryRegion:
    id: str
    climate_tags: list[str]
    context: dict[str, Any] = field(default_factory=dict)
    biome_id: str | None = None
    biome_mix: dict[str, Any] = field(default_factory=dict)
    region_archetype: str | None = None
    tier_min: int | None = None
    tier_max: int | None = None
    navigation_profile_id: str | None = None
    population_profile: dict[str, Any] = field(default_factory=dict)
    anchor_influence: dict[str, Any] = field(default_factory=dict)
    is_locked_frontier: bool = False


@dataclass(slots=True)
class MemoryZone:
    id: str
    region_id: str
    biome_id: str
    tier: int
    flags: dict[str, Any]
    zone_archetype: str
    navigation_profile_id: str
    landmark_profile: str | None
    population_tags: list[str]


@dataclass(slots=True)
class MemoryNode:
    x: int
    y: int
    zone_id: str
    biome_id: str | None
    node_type: str
    terrain_type: str
    navigation_profile_id: str
    buildable_kind: str | None
    landmark_profile: str | None
    movement_profile: dict[str, Any]
    background_key: str | None
    background_pool_key: str | None
    visual_overrides: dict[str, Any]
    services: list[str]
    content: dict[str, Any] | None
    is_active: bool
    flags: dict[str, Any]
    zone: MemoryZone | None = None


class InMemoryWorldData:
    def __init__(self) -> None:
        self.regions: dict[str, MemoryRegion] = {}
        self.zones: dict[str, MemoryZone] = {}
        self.nodes: dict[tuple[int, int], MemoryNode] = {}

    async def has_world_data(self) -> bool:
        return bool(self.nodes)

    async def count_active_nodes(self) -> int:
        return sum(1 for node in self.nodes.values() if node.is_active)

    async def get_active_nodes(self) -> list[MemoryNode]:
        return [node for node in self.nodes.values() if node.is_active]

    async def region_exists(self, region_id: str) -> bool:
        return region_id in self.regions

    async def get_zone(self, zone_id: str) -> WorldZoneSeed | None:
        zone = self.zones.get(zone_id)
        if zone is None:
            return None
        return WorldZoneSeed(
            id=zone.id,
            region_id=zone.region_id,
            biome_id=zone.biome_id,
            tier=zone.tier,
            zone_archetype=zone.zone_archetype,
            navigation_profile_id=zone.navigation_profile_id,
            landmark_profile=zone.landmark_profile,
            population_tags=list(zone.population_tags),
            flags=dict(zone.flags),
        )

    async def upsert_region(
        self,
        region_id: str,
        *,
        climate_tags: list[str],
        context: dict[str, Any] | None = None,
        biome_id: str | None = None,
        biome_mix: dict[str, Any] | None = None,
        region_archetype: str | None = None,
        tier_min: int | None = None,
        tier_max: int | None = None,
        navigation_profile_id: str | None = None,
        population_profile: dict[str, Any] | None = None,
        anchor_influence: dict[str, Any] | None = None,
        is_locked_frontier: bool = False,
    ) -> None:
        self.regions[region_id] = MemoryRegion(
            id=region_id,
            climate_tags=list(climate_tags),
            context=dict(context or {}),
            biome_id=biome_id,
            biome_mix=dict(biome_mix or {}),
            region_archetype=region_archetype,
            tier_min=tier_min,
            tier_max=tier_max,
            navigation_profile_id=navigation_profile_id,
            population_profile=dict(population_profile or {}),
            anchor_influence=dict(anchor_influence or {}),
            is_locked_frontier=is_locked_frontier,
        )

    async def upsert_zone(
        self,
        zone_id: str,
        *,
        region_id: str,
        biome_id: str,
        tier: int,
        flags: dict[str, Any],
        zone_archetype: str = "wild_core",
        navigation_profile_id: str = "open_frontier",
        landmark_profile: str | None = None,
        population_tags: list[str] | None = None,
    ) -> None:
        zone = MemoryZone(
            id=zone_id,
            region_id=region_id,
            biome_id=biome_id,
            tier=tier,
            flags=dict(flags),
            zone_archetype=zone_archetype,
            navigation_profile_id=navigation_profile_id,
            landmark_profile=landmark_profile,
            population_tags=list(population_tags or []),
        )
        self.zones[zone_id] = zone
        for node in self.nodes.values():
            if node.zone_id == zone_id:
                node.zone = zone

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def get_nodes_in_rect(self, x: int, y: int, width: int, height: int) -> list[MemoryNode]:
        return [
            node
            for node in self.nodes.values()
            if x <= node.x < x + width and y <= node.y < y + height
        ]

    async def bulk_upsert_nodes(self, nodes: list[dict[str, Any]]) -> None:
        for raw in nodes:
            zone_id = str(raw["zone_id"])
            self.nodes[(int(raw["x"]), int(raw["y"]))] = MemoryNode(
                x=int(raw["x"]),
                y=int(raw["y"]),
                zone_id=zone_id,
                biome_id=raw.get("biome_id"),
                node_type=str(raw.get("node_type") or "generic"),
                terrain_type=str(raw["terrain_type"]),
                navigation_profile_id=str(raw.get("navigation_profile_id") or "open_frontier"),
                buildable_kind=raw.get("buildable_kind"),
                landmark_profile=raw.get("landmark_profile"),
                movement_profile=dict(raw.get("movement_profile") or {}),
                background_key=raw.get("background_key"),
                background_pool_key=raw.get("background_pool_key"),
                visual_overrides=dict(raw.get("visual_overrides") or {}),
                services=list(raw.get("services") or []),
                content=dict(raw.get("content") or {}),
                is_active=bool(raw.get("is_active", False)),
                flags=dict(raw.get("flags") or {}),
                zone=self.zones.get(zone_id),
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the static world seed in memory and audit navigation/population shape.")
    parser.add_argument("--mode", choices=["test", "full"], default="full")
    parser.add_argument("--start", default="52_52", help="Reachability start coordinate, format x_y.")
    parser.add_argument("--region", default=None, help="Also generate and audit a non-D4 region node graph, e.g. C4.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    data = InMemoryWorldData()
    generator = LLMWorldGenerator(data, ai=None)  # no AI path: static generator only
    await generator.run(args.mode)

    start = parse_coord(args.start)
    nodes = [node for node in data.nodes.values() if node.is_active]
    nav_report = navigation_report(nodes, start=start)
    population_report = build_population_report(nodes)
    external_nodes = build_external_region_nodes(data, args.region) if args.region else []

    print_report(
        mode=args.mode,
        data=data,
        nodes=nodes,
        nav_report=nav_report,
        population_report=population_report,
        external_region=args.region,
        external_nodes=external_nodes,
    )


def parse_coord(raw: str) -> tuple[int, int]:
    x_raw, y_raw = raw.split("_", 1)
    return int(x_raw), int(y_raw)


def navigation_report(nodes: list[MemoryNode], *, start: tuple[int, int]) -> dict[str, Any]:
    service = WorldNavigationService()
    node_map = {f"{node.x}_{node.y}": node for node in nodes}
    exits_by_coord: dict[tuple[int, int], dict[str, Any]] = {}
    degree_counter: Counter[int] = Counter()
    for node in nodes:
        exits = {
            key: value
            for key, value in service.calculate_exits(node, node_map).items()
            if value.get("type") == "move"
        }
        exits_by_coord[(node.x, node.y)] = exits
        degree_counter[len(exits)] += 1

    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        coord = queue.popleft()
        if coord in visited:
            continue
        visited.add(coord)
        for exit_data in exits_by_coord.get(coord, {}).values():
            neighbor = exit_data["desc_next_room"]
            _ = neighbor
            key = next(
                (
                    nav_key
                    for nav_key, value in exits_by_coord.get(coord, {}).items()
                    if value is exit_data and nav_key.startswith("nav:")
                ),
                "",
            )
            if not key:
                continue
            x_raw, y_raw = key.removeprefix("nav:").split("_", 1)
            next_coord = (int(x_raw), int(y_raw))
            if next_coord not in visited:
                queue.append(next_coord)

    return {
        "reachable": len(visited),
        "unreachable": sorted((node.x, node.y) for node in nodes if (node.x, node.y) not in visited),
        "degree_counter": dict(sorted(degree_counter.items())),
        "dead_ends": sorted(coord for coord, exits in exits_by_coord.items() if len(exits) == 1),
        "isolated": sorted(coord for coord, exits in exits_by_coord.items() if not exits),
        "exits_by_coord": exits_by_coord,
    }


def build_population_report(nodes: list[MemoryNode]) -> list[dict[str, Any]]:
    service = WorldMonsterPopulationService(encounter_service=None)  # type: ignore[arg-type]
    contexts = service._build_unique_contexts(nodes)
    rows: list[dict[str, Any]] = []
    for context in sorted(contexts, key=lambda item: (item.tier, item.zone_id, item.biome_id, ",".join(item.tags))):
        normalized = normalize_tags(context.tags)
        rows.append(
            {
                "zone_id": context.zone_id,
                "tier": context.tier,
                "biome_id": context.biome_id,
                "tags": normalized,
                "families": available_family_ids(context.tier, context.biome_id, normalized),
                "context_hash": compute_context_hash(context.tier, context.biome_id, normalized),
                "rift_profile": context.context_meta.get("rift_profile") if context.context_meta else None,
            }
        )
    return rows


def available_family_ids(tier: int, biome_id: str, tags: list[str]) -> list[str]:
    in_biome = set(BIOME_FAMILIES.get(biome_id, set()))
    in_tier = set(TIER_AVAILABILITY.get(tier, set()))
    candidates = in_biome if "all_families" in in_tier else in_biome & in_tier
    if not candidates:
        candidates = in_tier - {"all_families"}
    family_bias = set(tags) & {"rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe"}
    if family_bias:
        candidates = candidates & family_bias
    return sorted(candidates)


def print_report(
    *,
    mode: str,
    data: InMemoryWorldData,
    nodes: list[MemoryNode],
    nav_report: dict[str, Any],
    population_report: list[dict[str, Any]],
    external_region: str | None,
    external_nodes: list[dict[str, Any]],
) -> None:
    print(f"world static audit: mode={mode}, ai=disabled, storage=in_memory")
    print(f"regions={len(data.regions)} zones={len(data.zones)} active_nodes={len(nodes)}")
    print()

    tier_counts = Counter(str((node.flags or {}).get("threat_tier", "unknown")) for node in nodes)
    node_type_counts = Counter(node.node_type for node in nodes)
    zone_counts = Counter(node.zone_id for node in nodes)
    print_counter("threat tiers", tier_counts)
    print_counter("node types", node_type_counts)
    print_counter("active nodes by zone", zone_counts)
    print()

    print("navigation")
    print(f"  reachable_from_52_52={nav_report['reachable']}/{len(nodes)}")
    print(f"  unreachable={len(nav_report['unreachable'])}")
    print(f"  isolated={len(nav_report['isolated'])}")
    print(f"  dead_ends={len(nav_report['dead_ends'])}")
    print(f"  degree_distribution={nav_report['degree_counter']}")
    if nav_report["unreachable"]:
        print(f"  first_unreachable={nav_report['unreachable'][:12]}")
    print()

    print("d4 rifts")
    for coord, profile in sorted(D4_RIFT_PROFILES.items()):
        node = data.nodes.get(coord)
        status = "ok" if node and node.flags.get("is_rift") and node.flags.get("threat_tier") == 2 else "bad"
        family_id = (node.flags.get("rift_profile") or {}).get("family_id") if node else None
        tags = (node.flags.get("rift_profile") or {}).get("context_tags") if node else None
        print(f"  {coord[0]}_{coord[1]} {status} id={profile['id']} family={family_id} tags={tags}")
    print()

    print("monster population contexts")
    print(f"  contexts={len(population_report)}")
    print(f"  estimated_clans={sum(len(row['families']) for row in population_report)}")
    for row in population_report:
        print(
            "  "
            f"tier={row['tier']} zone={row['zone_id']} biome={row['biome_id']} "
            f"hash={row['context_hash']} families={row['families']} tags={row['tags']}"
        )

    if external_region:
        print()
        print(f"external region node graph: {external_region}")
        if not external_nodes:
            print("  not_generated")
            return
        memory_nodes = [memory_node_from_raw(raw, None) for raw in external_nodes]
        start = (external_nodes[0]["x"] + 7, external_nodes[0]["y"] + 7)
        report = navigation_report(memory_nodes, start=start)
        print(f"  active_nodes={len(memory_nodes)}")
        print(f"  reachable_from_center={report['reachable']}/{len(memory_nodes)}")
        print(f"  unreachable={len(report['unreachable'])}")
        print(f"  isolated={len(report['isolated'])}")
        print(f"  dead_ends={len(report['dead_ends'])}")
        print(f"  degree_distribution={report['degree_counter']}")


def build_external_region_nodes(data: InMemoryWorldData, region_id: str | None) -> list[dict[str, Any]]:
    if not region_id or region_id == "D4":
        return []
    region = data.regions.get(region_id)
    if region is None:
        return []
    zones = {
        zone_id: WorldZoneSeed(
            id=zone.id,
            region_id=zone.region_id,
            biome_id=zone.biome_id,
            tier=zone.tier,
            zone_archetype=zone.zone_archetype,
            navigation_profile_id=zone.navigation_profile_id,
            landmark_profile=zone.landmark_profile,
            population_tags=list(zone.population_tags),
            flags=dict(zone.flags),
        )
        for zone_id, zone in data.zones.items()
        if zone.region_id == region_id
    }
    if len(zones) != 9:
        return []
    return WorldRegionNodeGenerator().build_nodes(
        RegionNodeGenerationInput(
            region_id=region_id,
            biome_id=str(region.biome_id or "wasteland"),
            region_archetype=str(region.region_archetype or "wild_region"),
            navigation_profile_id=str(region.navigation_profile_id or "open_frontier"),
            tier_min=int(region.tier_min or 0),
            tier_max=int(region.tier_max or 0),
            region_tags=list(region.climate_tags),
            zones=zones,
        )
    )


def memory_node_from_raw(raw: dict[str, Any], zone: MemoryZone | None) -> MemoryNode:
    return MemoryNode(
        x=int(raw["x"]),
        y=int(raw["y"]),
        zone_id=str(raw["zone_id"]),
        biome_id=raw.get("biome_id"),
        node_type=str(raw["node_type"]),
        terrain_type=str(raw["terrain_type"]),
        navigation_profile_id=str(raw["navigation_profile_id"]),
        buildable_kind=raw.get("buildable_kind"),
        landmark_profile=raw.get("landmark_profile"),
        movement_profile=dict(raw.get("movement_profile") or {}),
        background_key=raw.get("background_key"),
        background_pool_key=raw.get("background_pool_key"),
        visual_overrides=dict(raw.get("visual_overrides") or {}),
        services=list(raw.get("services") or []),
        content=dict(raw.get("content") or {}),
        is_active=bool(raw.get("is_active")),
        flags=dict(raw.get("flags") or {}),
        zone=zone,
    )


def print_counter(title: str, counter: Counter[str]) -> None:
    print(title)
    for key, count in sorted(counter.items()):
        print(f"  {key}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
