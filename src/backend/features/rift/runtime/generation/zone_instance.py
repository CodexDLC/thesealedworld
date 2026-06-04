from __future__ import annotations

import hashlib
import random
from collections import deque
from typing import Any, cast
from uuid import uuid4

from src.backend.features.rift.dto import (
    RiftPassageEdgeDTO,
    RiftPoolNodeDTO,
    RiftZoneCellDTO,
    RiftZonePlacementDTO,
    RiftZoneRuntimeDTO,
)
from src.backend.features.rift.dto.runtime import RiftRuntimePassageState, coord_key
from src.backend.features.rift.dto.screen import RiftAbsoluteDirection, RiftCoordinateDTO
from src.backend.features.rift.runtime.generation.canvas import CanvasBuilder
from src.backend.features.rift.runtime.generation.events import NodeEventSeeder
from src.backend.features.rift.runtime.generation.graph import PassageGraphBuilder
from src.backend.features.rift.runtime.generation.placement import NodePlacementService
from src.backend.features.rift.runtime.generation.planner import ZoneAssemblyPlanner
from src.backend.features.rift.runtime.geometry import ORDERED_DIRECTIONS, direction_between, neighbor_coord


def select_zone_assembly_plan(
    *,
    setting: dict[str, Any],
    scale_presets: dict[str, dict[str, Any]],
    assembly_presets: dict[str, dict[str, Any]],
    seed: str | None = None,
    requested_scale_key: str | None = None,
    requested_assembly_preset_key: str | None = None,
    use_default_scale: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return ZoneAssemblyPlanner().select_plan(
        setting=setting,
        scale_presets=scale_presets,
        assembly_presets=assembly_presets,
        seed=seed,
        requested_scale_key=requested_scale_key,
        requested_assembly_preset_key=requested_assembly_preset_key,
        use_default_scale=use_default_scale,
    )


def build_zone_runtime(
    *,
    setting: dict[str, Any],
    pool_nodes: dict[str, RiftPoolNodeDTO],
    scale_preset: dict[str, Any],
    assembly_preset: dict[str, Any],
    seed: str | None = None,
    void_cells: int | None = None,
    debug: bool = True,
    rift_instance_id: str | None = None,
    current_zone_key: str | None = None,
    zone_depth: int = 1,
) -> RiftZoneRuntimeDTO:
    canvas_builder = CanvasBuilder()
    graph_builder = PassageGraphBuilder()
    placement_service = NodePlacementService()
    event_seeder = NodeEventSeeder()
    grid = canvas_builder.grid(assembly_preset)
    assembly_key = str(assembly_preset.get("preset_key") or "zone")
    scale_key = str(scale_preset.get("preset_key") or "small")
    zone_key = str(assembly_preset.get("zone_key") or "z01")
    options = dict(setting.get("assembly_options") or {})
    resolved_seed = seed or str(options.get("default_seed") or "rift-dev")
    canvas_cells = canvas_builder.build_cells(zone_key=zone_key, width=grid["width"], height=grid["height"])
    canvas_cells_by_coord = {coord_key(node.x, node.y): node.node_id for node in canvas_cells.values()}
    rng = random.Random(f"{resolved_seed}:{assembly_key}:anchors")
    anchors = dict(assembly_preset.get("anchors") or {})
    start_node_id = canvas_builder.select_node_from_anchor_rules(
        canvas_cells_by_coord,
        raw_anchor_rules=anchors.get("start"),
        width=grid["width"],
        height=grid["height"],
        default_coordinate=RiftCoordinateDTO(x=0, y=grid["height"] // 2),
        rng=rng,
    )
    finish_node_id = canvas_builder.select_node_from_anchor_rules(
        canvas_cells_by_coord,
        raw_anchor_rules=anchors.get("finish"),
        width=grid["width"],
        height=grid["height"],
        default_coordinate=RiftCoordinateDTO(x=grid["width"] - 1, y=grid["height"] // 2),
        rng=rng,
    )
    requested_void_cells = canvas_builder.resolve_void_cells(
        assembly_preset=assembly_preset,
        requested_void_cells=void_cells,
        node_count=len(canvas_cells),
    )
    void_node_ids, passage_edges, finish_node_id = graph_builder.build_graph_state(
        assembly_preset=assembly_preset,
        nodes=canvas_cells,
        cells_by_coord=canvas_cells_by_coord,
        width=grid["width"],
        height=grid["height"],
        start_node_id=start_node_id,
        finish_node_id=finish_node_id,
        void_cells=max(0, min(requested_void_cells, max(0, len(canvas_cells) - 2))),
        seed=resolved_seed,
    )
    active_node_ids = set(canvas_cells) - void_node_ids
    placements, nodes = placement_service.build_placements(
        pool_nodes=pool_nodes,
        canvas_cells=canvas_cells,
        active_node_ids=active_node_ids,
        seed=resolved_seed,
        selection_policy=dict(assembly_preset.get("node_selection_policy") or {}),
        reserved_pool_node_ids=_reserved_pool_node_ids_by_cell(
            pool_nodes,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
        ),
    )
    node_events, node_states, gate_states = event_seeder.build_node_event_state(
        nodes=nodes,
        passage_edges=passage_edges,
        start_node_id=start_node_id,
        finish_node_id=finish_node_id,
        seed=resolved_seed,
    )
    cells_by_coord = {coord_key(node.x, node.y): node.node_id for node in nodes.values()}
    void_coords = [
        canvas_cells[node_id].coord
        for node_id in sorted(void_node_ids, key=lambda item: (canvas_cells[item].y, canvas_cells[item].x))
    ]
    heading = assembly_preset.get("default_heading")
    return RiftZoneRuntimeDTO(
        rift_instance_id=rift_instance_id or f"dev-rift-{_short_seed(resolved_seed)}-{uuid4().hex[:8]}",
        zone_instance_id=f"{assembly_key}:{zone_key}:instance",
        zone_canvas_key=assembly_key,
        scale_preset_key=scale_key,
        assembly_preset_key=assembly_key,
        setting=setting,
        scale_preset=scale_preset,
        assembly_preset=assembly_preset,
        placements=placements,
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        passage_edges=passage_edges,
        void_node_ids=void_node_ids,
        void_coords=void_coords,
        debug_map_width=grid["width"],
        debug_map_height=grid["height"],
        start_node_id=start_node_id,
        finish_node_id=finish_node_id,
        current_node_id=start_node_id,
        current_zone_key=current_zone_key or zone_key,
        zone_depth=zone_depth,
        zone_chain_order=[current_zone_key or zone_key],
        heading=heading if heading in ORDERED_DIRECTIONS else None,
        visited_node_ids={start_node_id},
        node_events=node_events,
        node_states=node_states,
        gate_states=gate_states,
        heart_state=_build_initial_heart_state(setting, finish_node_id=finish_node_id),
        population_context=build_population_context(setting),
        debug=debug,
    )


def _build_initial_heart_state(setting: dict[str, Any], *, finish_node_id: str) -> dict[str, Any]:
    screen = dict(setting.get("screen") or {})
    heart = dict(setting.get("heart") or {})
    value_by_tier = dict(heart.get("value_by_tier") or {})
    tier = max(1, int(heart.get("tier") or screen.get("tier") or 1))
    return {
        "heart_id": str(heart.get("heart_id") or f"{setting.get('setting_key', 'rift')}:heart"),
        "node_id": str(heart.get("node_id") or finish_node_id),
        "tier": tier,
        "base_value": int(heart.get("base_value") or value_by_tier.get(str(tier)) or value_by_tier.get(tier) or 100),
        "status": "intact",
        "methods": [
            {"method": "shatter", "label": "Разбить сердце", "enabled": True},
            {"method": "absorb", "label": "Поглотить энергию", "enabled": False, "locked_reason": "not_unlocked"},
            {
                "method": "dismantle",
                "label": "Демонтировать",
                "enabled": False,
                "locked_reason": "artifact_craft_required",
            },
        ],
        "can_exit": False,
        "completion": {"status": "active"},
    }


def build_population_context(setting: dict[str, Any]) -> dict[str, Any]:
    population = dict(setting.get("population_generation") or {})
    screen = dict(setting.get("screen") or {})
    setting_key = str(setting.get("setting_key") or "rift")
    habitat = dict(population.get("habitat") or {})
    biome_id = str(habitat.get("biome") or population.get("biome_id") or "wasteland")
    tier = max(1, int(population.get("tier") or population.get("threat_tier") or screen.get("tier") or 1))
    return {
        "source": "rift_habitat_clan_pool",
        "setting_key": setting_key,
        "biome_id": biome_id,
        "tier": tier,
        "habitat": {"biome": biome_id, "keys": _string_list(habitat.get("keys"))},
        "clan_pool_policy": dict(population.get("clan_pool_policy") or {}),
        "hash_strategy": "habitat_clan_pool_v1",
    }


def _reserved_pool_node_ids_by_cell(
    pool_nodes: dict[str, RiftPoolNodeDTO],
    *,
    start_node_id: str,
    finish_node_id: str,
) -> dict[str, str]:
    start_pool_node_id = _first_pool_node_id_with_roles(pool_nodes, role_keys={"start"})
    heart_pool_node_id = _first_pool_node_id_with_roles(
        pool_nodes, role_keys={"crystal_chamber", "objective"}, tag_keys={"rift_heart"}
    )
    reserved: dict[str, str] = {}
    if start_pool_node_id:
        reserved[start_node_id] = start_pool_node_id
    if heart_pool_node_id:
        reserved[finish_node_id] = heart_pool_node_id
    return reserved


def _first_pool_node_id_with_roles(
    pool_nodes: dict[str, RiftPoolNodeDTO],
    *,
    role_keys: set[str],
    tag_keys: set[str] | None = None,
) -> str | None:
    required_tags = tag_keys or set()
    for node in sorted(pool_nodes.values(), key=lambda item: (item.pool_order, item.pool_node_id)):
        roles = set(node.role_fit)
        tags = set(node.tags)
        if role_keys <= roles and required_tags <= tags:
            return node.pool_node_id
    return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, dict):
        values = [str(key).strip() for key, enabled in value.items() if bool(enabled)]
    elif isinstance(value, (list, tuple, set)):
        values = [str(item).strip() for item in value]
    else:
        values = []
    return sorted({item for item in values if item})


def rebuild_zone_state(
    runtime: RiftZoneRuntimeDTO,
    *,
    seed: str | None = None,
    void_cells: int | None = None,
) -> RiftZoneRuntimeDTO:
    graph_builder = PassageGraphBuilder()
    grid = _grid(runtime.assembly_preset)
    assembly_key = runtime.assembly_preset_key
    resolved_seed = seed or f"{runtime.rift_instance_id}:rebuild:{len(runtime.visited_node_ids)}"
    protected_node_ids = {
        runtime.start_node_id,
        runtime.finish_node_id,
        runtime.current_node_id,
        *runtime.visited_node_ids,
    }
    void_node_ids, passage_edges, finish_node_id = graph_builder.build_graph_state(
        assembly_preset=runtime.assembly_preset,
        nodes=runtime.nodes,
        cells_by_coord=runtime.cells_by_coord,
        width=grid["width"],
        height=grid["height"],
        start_node_id=runtime.start_node_id,
        finish_node_id=runtime.finish_node_id,
        void_cells=0,
        seed=f"{resolved_seed}:{assembly_key}",
        protected_node_ids=protected_node_ids,
        required_start_node_ids={runtime.start_node_id, runtime.current_node_id},
    )
    return runtime.model_copy(
        update={
            "void_node_ids": runtime.void_node_ids or void_node_ids,
            "passage_edges": passage_edges,
            "finish_node_id": finish_node_id,
            "last_travel": None,
        }
    )


def _build_graph_state(
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
    graph_policy = dict(assembly_preset.get("graph_policy") or {})
    if graph_policy.get("builder") == "main_path_branches":
        return _build_main_path_branch_graph(
            graph_policy=graph_policy,
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

    void_node_ids = _build_void_mask(
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
    return (
        void_node_ids,
        _build_adjacent_open_edges(nodes, cells_by_coord, width=width, height=height, void_node_ids=void_node_ids),
        finish_node_id,
    )


def _build_void_mask(
    *,
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
) -> set[str]:
    protected = {start_node_id, finish_node_id, *(protected_node_ids or set())}
    required_starts = required_start_node_ids or {start_node_id}
    candidates = [node_id for node_id in sorted(nodes) if node_id not in protected]
    rng = random.Random(seed)
    rng.shuffle(candidates)
    void_node_ids = set(candidates[:void_cells])

    while not _required_paths_exist(
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        width=width,
        height=height,
        start_node_ids=required_starts,
        finish_node_id=finish_node_id,
        void_node_ids=void_node_ids,
    ):
        blocked_start_node_id = _first_blocked_path_start(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_ids=required_starts,
            finish_node_id=finish_node_id,
            void_node_ids=void_node_ids,
        )
        removed = _select_unblock_candidate(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=blocked_start_node_id or start_node_id,
            finish_node_id=finish_node_id,
            void_node_ids=void_node_ids,
        )
        if removed is None:
            break
        void_node_ids.remove(removed)
    return void_node_ids


def _build_main_path_branch_graph(
    *,
    graph_policy: dict[str, Any],
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
    rng = random.Random(f"{seed}:main-path-branches")
    _ = required_start_node_ids
    protected = {start_node_id, finish_node_id, *(protected_node_ids or set())}
    target_open_count = max(len(nodes) - void_cells, len(protected), 2)
    open_node_ids = {start_node_id}
    tree_edges: set[tuple[str, str]] = set()
    branch_policy = dict(graph_policy.get("branches") or {})
    for protected_node_id in protected - open_node_ids:
        protected_path = _shortest_path(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=start_node_id,
            finish_node_id=protected_node_id,
        )
        _add_path_to_tree(protected_path, open_node_ids=open_node_ids, tree_edges=tree_edges)

    while len(open_node_ids) < target_open_count:
        before = len(open_node_ids)
        _grow_tree_branch(
            open_node_ids=open_node_ids,
            tree_edges=tree_edges,
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            rng=rng,
            length=_rng_range(rng, branch_policy.get("branch_length_range"), default_min=1, default_max=4),
            target_open_count=target_open_count,
        )
        if len(open_node_ids) == before:
            break

    finish_node_id = _deep_finish_node_by_edges(
        start_node_id,
        open_node_ids=open_node_ids,
        tree_edges=tree_edges,
        nodes=nodes,
        width=width,
        height=height,
    )
    void_node_ids = set(nodes) - open_node_ids
    passage_edges: dict[str, RiftPassageEdgeDTO] = {}
    for left_node_id, right_node_id in sorted(tree_edges):
        _add_bidirectional_edge(
            passage_edges,
            nodes=nodes,
            from_node_id=left_node_id,
            to_node_id=right_node_id,
            state="open",
        )
    soft_wall_count = _rng_range(rng, branch_policy.get("shortcut_count_range"), default_min=2, default_max=5)
    _add_temporary_shortcut_edges(
        passage_edges,
        open_node_ids=open_node_ids,
        tree_edges=tree_edges,
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        width=width,
        height=height,
        rng=rng,
        count=soft_wall_count,
    )
    return void_node_ids, passage_edges, finish_node_id


def _add_path_to_tree(path: list[str], *, open_node_ids: set[str], tree_edges: set[tuple[str, str]]) -> None:
    for node_id in path:
        open_node_ids.add(node_id)
    for left_node_id, right_node_id in zip(path, path[1:], strict=False):
        tree_edges.add(_edge_pair(left_node_id, right_node_id))


def _grow_tree_branch(
    *,
    open_node_ids: set[str],
    tree_edges: set[tuple[str, str]],
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    rng: random.Random,
    length: int,
    target_open_count: int,
) -> None:
    source_node_id = _select_branch_source(
        open_node_ids,
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        width=width,
        height=height,
        rng=rng,
    )
    if source_node_id is None:
        return
    current_node_id = source_node_id
    for _ in range(max(1, length)):
        if len(open_node_ids) >= target_open_count:
            return
        candidates = [
            neighbor_id
            for neighbor_id in _neighbor_ids(nodes[current_node_id], cells_by_coord, width=width, height=height)
            if neighbor_id not in open_node_ids
        ]
        if not candidates:
            return
        next_node_id = rng.choice(candidates)
        open_node_ids.add(next_node_id)
        tree_edges.add(_edge_pair(current_node_id, next_node_id))
        current_node_id = next_node_id


def _deep_finish_node_by_edges(
    start_node_id: str,
    *,
    open_node_ids: set[str],
    tree_edges: set[tuple[str, str]],
    nodes: dict[str, RiftZoneCellDTO],
    width: int,
    height: int,
) -> str:
    distances = _edge_distances_from_start(start_node_id, open_node_ids=open_node_ids, tree_edges=tree_edges)
    start = nodes[start_node_id]
    candidates = [node_id for node_id in sorted(open_node_ids) if node_id != start_node_id]
    min_spatial_distance = max(3, min(width, height) // 2)
    spatial_candidates = [
        node_id for node_id in candidates if _manhattan(start, nodes[node_id]) >= min_spatial_distance
    ]
    pool = spatial_candidates or candidates
    if not pool:
        return start_node_id
    return max(
        pool,
        key=lambda node_id: (
            distances.get(node_id, -1),
            _manhattan(start, nodes[node_id]),
            nodes[node_id].x,
            nodes[node_id].y,
        ),
    )


def _edge_distances_from_start(
    start_node_id: str,
    *,
    open_node_ids: set[str],
    tree_edges: set[tuple[str, str]],
) -> dict[str, int]:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in open_node_ids}
    for left_node_id, right_node_id in tree_edges:
        if left_node_id in adjacency and right_node_id in adjacency:
            adjacency[left_node_id].append(right_node_id)
            adjacency[right_node_id].append(left_node_id)
    queue: deque[tuple[str, int]] = deque([(start_node_id, 0)])
    seen: set[str] = set()
    distances: dict[str, int] = {}
    while queue:
        node_id, distance = queue.popleft()
        if node_id in seen:
            continue
        seen.add(node_id)
        distances[node_id] = distance
        for neighbor_id in adjacency.get(node_id, []):
            if neighbor_id not in seen:
                queue.append((neighbor_id, distance + 1))
    return distances


def _add_temporary_shortcut_edges(
    passage_edges: dict[str, RiftPassageEdgeDTO],
    *,
    open_node_ids: set[str],
    tree_edges: set[tuple[str, str]],
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    rng: random.Random,
    count: int,
) -> None:
    candidates: list[tuple[str, str]] = []
    for node_id in sorted(open_node_ids):
        node = nodes[node_id]
        for neighbor_id in _neighbor_ids(node, cells_by_coord, width=width, height=height):
            pair = _edge_pair(node_id, neighbor_id)
            if neighbor_id in open_node_ids and pair not in tree_edges and pair not in candidates:
                candidates.append(pair)
    rng.shuffle(candidates)
    for left_node_id, right_node_id in candidates[: max(0, count)]:
        check = _temporary_blocker_check(rng)
        _add_bidirectional_edge(
            passage_edges,
            nodes=nodes,
            from_node_id=left_node_id,
            to_node_id=right_node_id,
            state="blocked_temporary",
            blocker_key="jammed_service_gate",
            requirement={
                "type": "skill_or_attribute_check",
                "mode": "single_attribute",
                "check": check,
                "checks": [check],
                "status": "contract_only",
            },
        )


def _temporary_blocker_check(rng: random.Random) -> dict[str, Any]:
    return rng.choice(
        [
            {"kind": "attribute", "key": "strength", "dc": 15, "label": "Разломать частокол"},
            {"kind": "attribute", "key": "intelligence", "dc": 15, "label": "Найти слабый крепеж"},
            {"kind": "attribute", "key": "dexterity", "dc": 15, "label": "Пролезть в просвет"},
        ]
    )


def _build_adjacent_open_edges(
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    *,
    width: int,
    height: int,
    void_node_ids: set[str],
) -> dict[str, RiftPassageEdgeDTO]:
    passage_edges: dict[str, RiftPassageEdgeDTO] = {}
    for node_id, node in nodes.items():
        if node_id in void_node_ids:
            continue
        for neighbor_id in _neighbor_ids(node, cells_by_coord, width=width, height=height):
            if neighbor_id not in void_node_ids:
                _add_bidirectional_edge(
                    passage_edges, nodes=nodes, from_node_id=node_id, to_node_id=neighbor_id, state="open"
                )
    return passage_edges


def _add_bidirectional_edge(
    passage_edges: dict[str, RiftPassageEdgeDTO],
    *,
    nodes: dict[str, RiftZoneCellDTO],
    from_node_id: str,
    to_node_id: str,
    state: RiftRuntimePassageState,
    blocker_key: str | None = None,
    requirement: dict[str, Any] | None = None,
) -> None:
    from_node = nodes[from_node_id]
    to_node = nodes[to_node_id]
    direction = direction_between(from_node.coord, to_node.coord)
    reverse_direction = direction_between(to_node.coord, from_node.coord)
    if direction is None or reverse_direction is None:
        return
    passage_edges[_edge_key(from_node_id, direction)] = RiftPassageEdgeDTO(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        absolute_direction=direction,
        state=state,
        blocker_key=blocker_key,
        requirement=requirement or {},
    )
    passage_edges[_edge_key(to_node_id, reverse_direction)] = RiftPassageEdgeDTO(
        from_node_id=to_node_id,
        to_node_id=from_node_id,
        absolute_direction=reverse_direction,
        state=state,
        blocker_key=blocker_key,
        requirement=requirement or {},
    )


def _edge_key(node_id: str, direction: RiftAbsoluteDirection) -> str:
    return f"{node_id}:{direction}"


def _edge_pair(left_node_id: str, right_node_id: str) -> tuple[str, str]:
    return cast("tuple[str, str]", tuple(sorted((left_node_id, right_node_id))))


def _build_main_path(
    *,
    graph_policy: dict[str, Any],
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_id: str,
    finish_node_id: str,
    seed: str,
) -> list[str]:
    main_path_policy = dict(graph_policy.get("main_path") or {})
    attempts = int(main_path_policy.get("attempts") or 24)
    node_count = len(nodes)
    min_path_length = max(2, round(node_count * float(main_path_policy.get("min_length_ratio") or 0.35)))
    max_path_length = max(min_path_length, round(node_count * float(main_path_policy.get("max_length_ratio") or 0.8)))
    best_path: list[str] = []
    backup_path: list[str] = []
    for attempt in range(max(1, attempts)):
        rng = random.Random(f"{seed}:main-path:{attempt}")
        path = _randomized_dfs_path(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
            rng=rng,
        )
        if not path:
            continue
        if not backup_path or len(path) < len(backup_path):
            backup_path = path
        if min_path_length <= len(path) <= max_path_length and len(path) > len(best_path):
            best_path = path
    return (
        best_path
        or backup_path
        or _shortest_path(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
        )
    )


def _randomized_dfs_path(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_id: str,
    finish_node_id: str,
    rng: random.Random,
) -> list[str]:
    stack = [start_node_id]
    parent: dict[str, str | None] = {start_node_id: None}
    seen = {start_node_id}
    while stack:
        node_id = stack[-1]
        if node_id == finish_node_id:
            return _reconstruct_path(parent, finish_node_id)
        candidates = [
            neighbor_id
            for neighbor_id in _neighbor_ids(nodes[node_id], cells_by_coord, width=width, height=height)
            if neighbor_id not in seen
        ]
        if not candidates:
            stack.pop()
            continue
        rng.shuffle(candidates)
        next_node_id = candidates[0]
        parent[next_node_id] = node_id
        seen.add(next_node_id)
        stack.append(next_node_id)
    return []


def _shortest_path(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_id: str,
    finish_node_id: str,
) -> list[str]:
    queue: deque[str] = deque([start_node_id])
    parent: dict[str, str | None] = {start_node_id: None}
    while queue:
        node_id = queue.popleft()
        if node_id == finish_node_id:
            return _reconstruct_path(parent, finish_node_id)
        for neighbor_id in _neighbor_ids(nodes[node_id], cells_by_coord, width=width, height=height):
            if neighbor_id not in parent:
                parent[neighbor_id] = node_id
                queue.append(neighbor_id)
    return [start_node_id, finish_node_id]


def _reconstruct_path(parent: dict[str, str | None], finish_node_id: str) -> list[str]:
    result = [finish_node_id]
    current = finish_node_id
    while parent.get(current) is not None:
        current = parent[current] or ""
        result.append(current)
    result.reverse()
    return result


def _grow_branch(
    *,
    open_node_ids: set[str],
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    rng: random.Random,
    length: int,
    target_open_count: int,
) -> None:
    source_node_id = _select_branch_source(
        open_node_ids,
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        width=width,
        height=height,
        rng=rng,
    )
    if source_node_id is None:
        return
    current_node_id = source_node_id
    for _ in range(max(1, length)):
        if len(open_node_ids) >= target_open_count:
            return
        candidates = [
            neighbor_id
            for neighbor_id in _neighbor_ids(nodes[current_node_id], cells_by_coord, width=width, height=height)
            if neighbor_id not in open_node_ids
        ]
        if not candidates:
            return
        low_connection_candidates = [
            node_id
            for node_id in candidates
            if _open_neighbor_count(
                node_id, open_node_ids, nodes=nodes, cells_by_coord=cells_by_coord, width=width, height=height
            )
            <= 1
        ]
        pool = low_connection_candidates or candidates
        next_node_id = rng.choice(pool)
        open_node_ids.add(next_node_id)
        current_node_id = next_node_id


def _select_branch_source(
    open_node_ids: set[str],
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    rng: random.Random,
) -> str | None:
    candidates = [
        node_id
        for node_id in open_node_ids
        if any(
            neighbor_id not in open_node_ids
            for neighbor_id in _neighbor_ids(nodes[node_id], cells_by_coord, width=width, height=height)
        )
    ]
    return rng.choice(candidates) if candidates else None


def _open_neighbor_count(
    node_id: str,
    open_node_ids: set[str],
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
) -> int:
    return sum(
        1
        for neighbor_id in _neighbor_ids(nodes[node_id], cells_by_coord, width=width, height=height)
        if neighbor_id in open_node_ids
    )


def _has_branch_shape(
    open_node_ids: set[str],
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
) -> bool:
    return any(
        _open_neighbor_count(
            node_id, open_node_ids, nodes=nodes, cells_by_coord=cells_by_coord, width=width, height=height
        )
        >= 3
        for node_id in open_node_ids
    )


def _rng_range(rng: random.Random, raw_range: Any, *, default_min: int, default_max: int) -> int:
    if not isinstance(raw_range, dict):
        return rng.randint(default_min, default_max)
    minimum = int(raw_range.get("min", default_min))
    maximum = int(raw_range.get("max", default_max))
    return rng.randint(minimum, max(minimum, maximum))


def _required_paths_exist(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_ids: set[str],
    finish_node_id: str,
    void_node_ids: set[str],
) -> bool:
    return all(
        _path_exists(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
            void_node_ids=void_node_ids,
        )
        for start_node_id in start_node_ids
    )


def _first_blocked_path_start(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_ids: set[str],
    finish_node_id: str,
    void_node_ids: set[str],
) -> str | None:
    for start_node_id in sorted(start_node_ids):
        if not _path_exists(
            nodes=nodes,
            cells_by_coord=cells_by_coord,
            width=width,
            height=height,
            start_node_id=start_node_id,
            finish_node_id=finish_node_id,
            void_node_ids=void_node_ids,
        ):
            return start_node_id
    return None


def _path_exists(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_id: str,
    finish_node_id: str,
    void_node_ids: set[str],
) -> bool:
    return finish_node_id in _reachable_nodes(
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        width=width,
        height=height,
        start_node_id=start_node_id,
        void_node_ids=void_node_ids,
    )


def _reachable_nodes(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_id: str,
    void_node_ids: set[str],
) -> set[str]:
    queue: deque[str] = deque([start_node_id])
    seen: set[str] = set()
    while queue:
        node_id = queue.popleft()
        if node_id in seen or node_id in void_node_ids:
            continue
        seen.add(node_id)
        node = nodes[node_id]
        for neighbor_id in _neighbor_ids(node, cells_by_coord, width=width, height=height):
            if neighbor_id not in seen and neighbor_id not in void_node_ids:
                queue.append(neighbor_id)
    return seen


def _select_unblock_candidate(
    *,
    nodes: dict[str, RiftZoneCellDTO],
    cells_by_coord: dict[str, str],
    width: int,
    height: int,
    start_node_id: str,
    finish_node_id: str,
    void_node_ids: set[str],
) -> str | None:
    if not void_node_ids:
        return None
    reachable = _reachable_nodes(
        nodes=nodes,
        cells_by_coord=cells_by_coord,
        width=width,
        height=height,
        start_node_id=start_node_id,
        void_node_ids=void_node_ids,
    )
    finish = nodes[finish_node_id]
    adjacent_blocked: list[str] = []
    for node_id in sorted(reachable):
        node = nodes[node_id]
        for neighbor_id in _neighbor_ids(node, cells_by_coord, width=width, height=height):
            if neighbor_id in void_node_ids:
                adjacent_blocked.append(neighbor_id)
    if adjacent_blocked:
        return min(adjacent_blocked, key=lambda node_id: _manhattan(nodes[node_id], finish))
    return min(void_node_ids, key=lambda node_id: _manhattan(nodes[node_id], finish))


def _neighbor_ids(
    node: RiftZoneCellDTO,
    cells_by_coord: dict[str, str],
    *,
    width: int,
    height: int,
) -> list[str]:
    result: list[str] = []
    coord = RiftCoordinateDTO(x=node.x, y=node.y)
    for direction in ORDERED_DIRECTIONS:
        neighbor = neighbor_coord(coord, direction)
        if neighbor.x < 0 or neighbor.y < 0 or neighbor.x >= width or neighbor.y >= height:
            continue
        node_id = cells_by_coord.get(f"{neighbor.x}:{neighbor.y}")
        if node_id:
            result.append(node_id)
    return result


def _select_node_from_anchor_rules(
    cells_by_coord: dict[str, str],
    *,
    raw_anchor_rules: Any,
    width: int,
    height: int,
    default_coordinate: RiftCoordinateDTO,
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
    default_node_id = cells_by_coord.get(coord_key(default_coordinate.x, default_coordinate.y))
    if default_node_id is None:
        raise ValueError("Rift canvas does not contain a usable start/finish coordinate")
    return default_node_id


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


def _build_canvas_cells(*, zone_key: str, width: int, height: int) -> dict[str, RiftZoneCellDTO]:
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


def _build_placements(
    *,
    pool_nodes: dict[str, RiftPoolNodeDTO],
    canvas_cells: dict[str, RiftZoneCellDTO],
    active_node_ids: set[str],
    seed: str,
    selection_policy: dict[str, Any],
) -> tuple[list[RiftZonePlacementDTO], dict[str, RiftZoneCellDTO]]:
    active_canvas_cells = [
        canvas_cells[node_id]
        for node_id in sorted(active_node_ids, key=lambda item: (canvas_cells[item].y, canvas_cells[item].x))
    ]
    required_count = len(active_canvas_cells)
    selected = sorted(pool_nodes.values(), key=lambda node: (node.pool_order, node.pool_node_id))
    if selection_policy.get("selection_mode") == "stable_shuffle":
        canvas_signature = ":".join(node.node_id for node in active_canvas_cells)
        rng = random.Random(f"{seed}:node-selection:{canvas_signature}")
        rng.shuffle(selected)
    selected = selected[:required_count]
    if len(selected) < required_count:
        raise ValueError(f"Rift node pool needs {required_count} nodes, got {len(selected)}")

    placements: list[RiftZonePlacementDTO] = []
    cells: dict[str, RiftZoneCellDTO] = {}
    for canvas_cell, pool_node in zip(active_canvas_cells, selected, strict=True):
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


def _grid(assembly_preset: dict[str, Any]) -> dict[str, int]:
    grid = dict(assembly_preset.get("geometry") or {})
    return {"width": int(grid.get("width") or 5), "height": int(grid.get("height") or 5)}


def _resolve_void_cells(*, assembly_preset: dict[str, Any], requested_void_cells: int | None, node_count: int) -> int:
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


def _allowed_keys(raw_keys: Any, presets: dict[str, dict[str, Any]]) -> list[str]:
    if not isinstance(raw_keys, list):
        return sorted(presets)
    result = [key for key in raw_keys if isinstance(key, str) and key in presets]
    if not result:
        raise ValueError("Rift preset allow-list does not contain usable keys")
    return result


def _manhattan(left: RiftZoneCellDTO, right: RiftZoneCellDTO) -> int:
    return abs(left.x - right.x) + abs(left.y - right.y)


def _short_seed(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
