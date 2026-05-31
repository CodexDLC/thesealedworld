from __future__ import annotations

from collections import deque

import pytest

from src.backend.features.monsters.runtime.hashing import compute_rift_context_hash
from src.backend.features.rift.dto import RiftZoneRuntimeDTO
from src.backend.features.rift.dto.runtime import RiftActionRequestDTO, coord_key
from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.runtime.generation import (
    build_zone_chain_runtime,
    build_zone_runtime,
    rebuild_zone_state,
    select_zone_assembly_plan,
)
from src.backend.features.rift.runtime.geometry import ORDERED_DIRECTIONS, neighbor_coord
from src.backend.features.rift.runtime.navigation import (
    build_rift_screen,
    resolve_node_entry_event_runtime,
    resolve_rift_action_runtime,
    resolve_transition_combat_runtime,
    start_travel_runtime,
    tick_travel_runtime,
)
from src.backend.features.rift.runtime.tunables import (
    DEFAULT_TRANSITION_OPENING_CONTEXT,
    RiftTunables,
    use_tunables,
)


@pytest.mark.unit
def test_starter_rift_runtime_keeps_path_after_void_mask() -> None:
    runtime = _runtime(seed="path-check", void_cells=10)

    assert all(node.pool_node_id for node in runtime.nodes.values())
    assert runtime.start_node_id not in runtime.void_node_ids
    assert runtime.finish_node_id not in runtime.void_node_ids
    guard_node_id = next(iter(runtime.node_events))
    assert guard_node_id in _reachable(runtime, runtime.start_node_id)
    assert runtime.finish_node_id not in _reachable(runtime, runtime.start_node_id)
    unlocked, _response = resolve_node_entry_event_runtime(
        runtime.model_copy(update={"current_node_id": guard_node_id}),
        event_key="guard_combat",
    )
    assert runtime.finish_node_id in _reachable_effective(unlocked, runtime.start_node_id)
    assert len(runtime.void_node_ids) <= 10


@pytest.mark.unit
def test_starter_rift_heart_has_no_temporary_bypass_before_guard() -> None:
    for index in range(40):
        runtime = _runtime(seed=f"probe-{index}", void_cells=10)
        guard_node_id = next(iter(runtime.node_events))
        incoming_edges = [edge for edge in runtime.passage_edges.values() if edge.to_node_id == runtime.finish_node_id]
        guarded_edges = [edge for edge in incoming_edges if edge.from_node_id == guard_node_id]
        bypass_edges = [
            edge
            for edge in incoming_edges
            if edge.from_node_id != guard_node_id and edge.state in {"open", "blocked_temporary", "locked"}
        ]

        assert guarded_edges
        assert all(edge.state == "locked" for edge in guarded_edges)
        assert bypass_edges == []


@pytest.mark.unit
def test_node_pool_has_no_coordinates_before_zone_instance_placement() -> None:
    resources = RiftResourceLoader()
    setting = resources.load_setting("starter_rift")
    pool_nodes = resources.load_node_pool("starter_rift")
    dev_character = resources.load_dev_character_snapshot()

    assert setting["setting_key"] == "starter_rift"
    assert "grid_defaults" not in setting
    assert "dev_action_context" not in setting
    assert dev_character["character"]["attributes"] == {"strength": 14, "intelligence": 16, "dexterity": 12}
    assert setting["screen"]["tier"] == 1
    assert setting["heart"]["tier"] == 1
    assert setting["heart"]["value_by_tier"]["1"] == 100
    assert setting["heart"]["value_by_tier"]["2"] == 1000
    assert setting["population_generation"]["strategy"] == "rift_static_hash"
    assert setting["population_generation"]["tier"] == 1
    assert setting["population_generation"]["selection_profile_id"] == "starter_broken_road_raiders"
    assert setting["population_generation"]["selection_tags"] == ["humanoid", "raider", "scavenger", "roadside_camp"]
    assert [slot["slot_id"] for slot in setting["population_generation"]["family_slots"]] == [
        "primary",
        "secondary",
    ]
    assert "family_ids" not in setting["population_generation"]
    assert "transition_combat_rules" not in setting
    assert "ordinary_node_combat_rules" not in setting
    assert DEFAULT_TRANSITION_OPENING_CONTEXT["status"] == "contract_placeholder"
    assert {
        item["skill_key"]
        for item in DEFAULT_TRANSITION_OPENING_CONTEXT["skill_hooks"]
    } == {
        "skill_scouting",
        "skill_pathfinder",
        "skill_hunting",
        "skill_adaptation",
        "skill_tactics",
    }
    assert pool_nodes
    assert len(pool_nodes) == 15
    assert all(node.pool_node_id.startswith("starter_rift:") for node in pool_nodes.values())
    assert all(not hasattr(node, "x") and not hasattr(node, "y") for node in pool_nodes.values())


@pytest.mark.unit
def test_loader_reads_scale_and_zone_assembly_presets() -> None:
    resources = RiftResourceLoader()

    scale_presets = resources.load_scale_presets()
    assembly_presets = resources.load_zone_assembly_presets()

    assert {"small", "medium", "large", "xl"} <= set(scale_presets)
    assert {"chain_2x_grid_4x4_active_12", "grid_5x5_active_15", "grid_6x6_active_20", "grid_7x7_active_25"} <= set(assembly_presets)
    assert "grid_3x3_core" not in assembly_presets
    assert "grid_4x3_compact" not in assembly_presets
    assert "grid_4x4_box" not in assembly_presets
    assert "grid_4x5_vertical" not in assembly_presets
    assert assembly_presets["chain_2x_grid_4x4_active_12"]["geometry"] == {"width": 4, "height": 4}
    assert assembly_presets["chain_2x_grid_4x4_active_12"]["active_nodes"]["target"] == 12
    assert assembly_presets["chain_2x_grid_4x4_active_12"]["zone_chain"]["levels"] == 2
    assert assembly_presets["grid_5x5_active_15"]["geometry"] == {"width": 5, "height": 5}
    assert assembly_presets["grid_5x5_active_15"]["active_nodes"]["target"] == 15
    assert assembly_presets["grid_6x6_active_20"]["active_nodes"]["target"] == 20
    assert assembly_presets["grid_7x7_active_25"]["active_nodes"]["target"] == 25


@pytest.mark.unit
def test_zone_runtime_uses_assembly_preset_geometry() -> None:
    resources = RiftResourceLoader()
    assembly_presets = resources.load_zone_assembly_presets()
    runtime = build_zone_runtime(
        setting=resources.load_setting("starter_rift"),
        pool_nodes=_expanded_pool_nodes(resources.load_node_pool("starter_rift"), target=20),
        scale_preset=resources.load_scale_presets()["medium"],
        assembly_preset=assembly_presets["grid_6x6_active_20"],
        seed="assembly-geometry-check",
        debug=True,
    )

    assert runtime.scale_preset_key == "medium"
    assert runtime.assembly_preset_key == "grid_6x6_active_20"
    assert runtime.zone_canvas_key == "grid_6x6_active_20"
    assert len(runtime.nodes) == 20
    assert len(runtime.placements) == 20
    assert runtime.debug_map_width == 6
    assert runtime.debug_map_height == 6
    assert len(runtime.void_coords) == 16


@pytest.mark.unit
def test_starter_rift_reserves_start_and_heart_content_nodes() -> None:
    runtime = _runtime(seed="starter-rift-dev", void_cells=10)
    start = runtime.nodes[runtime.start_node_id]
    heart = runtime.nodes[runtime.finish_node_id]

    assert start.pool_node_id == "starter_rift:001_broken_milestone"
    assert start.title == "Вход у разбитой вехи"
    assert "start" in start.role_fit
    assert runtime.heart_state["node_id"] == runtime.finish_node_id
    assert heart.pool_node_id == "starter_rift:015_rift_heart"
    assert heart.title == "Сердце рваного тракта"
    assert {"rift_heart", "objective"} <= set(heart.tags)
    assert {"crystal_chamber", "objective"} <= set(heart.role_fit)


@pytest.mark.unit
def test_zone_runtime_builds_rift_population_context_with_rift_hash() -> None:
    runtime = _runtime(seed="population-context-check", void_cells=5)
    population = runtime.population_context
    expected_hash = compute_rift_context_hash(
        setting_key="starter_rift",
        biome_id="broken_road",
        tier=1,
        tags=[
            "starter_rift",
            "tier_1_rift",
            "broken_caravan",
            "roadside_camp",
            "bandit_scavengers",
            "rift_scavenger_beasts",
        ],
    )

    assert population["source"] == "rift_static"
    assert population["setting_key"] == "starter_rift"
    assert population["biome_id"] == "broken_road"
    assert population["tier"] == 1
    assert population["selection_profile_id"] == "starter_broken_road_raiders"
    assert population["selection_tags"] == ["humanoid", "raider", "roadside_camp", "scavenger"]
    assert [slot["slot_id"] for slot in population["family_slots"]] == ["primary", "secondary"]
    assert population["family_slots"][0]["selection_tags"] == ["camp_guard", "humanoid", "raider", "roadside_camp"]
    assert population["family_slots"][0]["prototype_family_key"] == "bandit_gang"
    assert population["family_slots"][0]["family_id"] == "bandit_gang"
    assert population["family_slots"][1]["selection_tags"] == ["beast", "broken_caravan", "rat", "scavenger"]
    assert population["family_slots"][1]["prototype_family_key"] == "rat_swarm"
    assert population["family_bindings"]["secondary"]["family_id"] == "rat_swarm"
    assert population["family_slots"][0]["context_hash"] != population["family_slots"][1]["context_hash"]
    assert population["family_slots"][0]["unique_hash"] == population["family_bindings"]["primary"]["unique_hash"]
    assert population["family_bindings"]["primary"]["family_id"] == "bandit_gang"
    assert population["family_bindings"]["primary"]["clan_id"] is None
    assert population["family_bindings"]["primary"]["context_hash"] == population["family_slots"][0]["context_hash"]
    assert "family_ids" not in population
    assert population["context_hash"] == expected_hash
    assert "broken_caravan" in population["tags"]


@pytest.mark.unit
def test_zone_runtime_places_only_active_nodes_inside_larger_canvas() -> None:
    resources = RiftResourceLoader()
    assembly_presets = resources.load_zone_assembly_presets()
    runtime = build_zone_runtime(
        setting=resources.load_setting("starter_rift"),
        pool_nodes=_expanded_pool_nodes(resources.load_node_pool("starter_rift"), target=25),
        scale_preset=resources.load_scale_presets()["medium"],
        assembly_preset=assembly_presets["grid_7x7_active_25"],
        seed="large-canvas-active-node-check",
        debug=True,
    )
    screen = build_rift_screen(runtime)

    assert len(runtime.nodes) == 25
    assert len(runtime.placements) == 25
    assert runtime.debug_map_width == 7
    assert runtime.debug_map_height == 7
    assert len(runtime.void_coords) == 24
    assert screen.debug_map is not None
    assert len(screen.debug_map.cells) == 49
    assert sum(1 for cell in screen.debug_map.cells if cell.state == "void") == 24


@pytest.mark.unit
def test_zone_chain_runtime_builds_two_4x4_levels_and_switches_after_gate_guard() -> None:
    resources = RiftResourceLoader()
    runtime = build_zone_chain_runtime(
        setting=resources.load_setting("starter_rift"),
        pool_nodes=_expanded_pool_nodes(resources.load_node_pool("starter_rift"), target=24),
        scale_preset=resources.load_scale_presets()["medium"],
        assembly_preset=resources.load_zone_assembly_presets()["chain_2x_grid_4x4_active_12"],
        seed="two-level-chain-check",
        debug=True,
    )

    assert runtime.current_zone_key == "z01"
    assert runtime.zone_depth == 1
    assert runtime.zone_chain_order == ["z01", "z02"]
    assert set(runtime.zone_chain) == {"z01", "z02"}
    assert runtime.debug_map_width == 4
    assert runtime.debug_map_height == 4
    assert len(runtime.nodes) == 12
    assert len(runtime.placements) == 12
    second_zone = RiftZoneRuntimeDTO.model_validate(runtime.zone_chain["z02"])
    assert second_zone.current_zone_key == "z02"
    assert second_zone.zone_depth == 2
    assert second_zone.debug_map_width == 4
    assert second_zone.debug_map_height == 4
    assert len(second_zone.nodes) == 12
    assert {item.pool_node_id for item in runtime.placements}.isdisjoint(
        {item.pool_node_id for item in second_zone.placements}
    )

    travelling = runtime
    guard_node_id = next(
        node_id for node_id, event in travelling.node_events.items() if event.get("event_key") == "guard_combat"
    )
    for target_node_id in _open_path(travelling, travelling.start_node_id, guard_node_id)[1:]:
        travelling = _complete_travel(travelling, target_node_id)
    travelling, _guard_response = resolve_node_entry_event_runtime(travelling, event_key="guard_combat")
    for target_node_id in _open_path_effective(travelling, travelling.current_node_id, travelling.finish_node_id)[1:]:
        travelling = _complete_travel(travelling, target_node_id)

    gate_screen = build_rift_screen(travelling)
    assert travelling.current_node_id == travelling.finish_node_id
    assert gate_screen.node_entry_event.state == "ready"
    assert gate_screen.node_entry_event.event_key == "next_zone_guard"
    assert gate_screen.node_entry_event.metadata["unlocks"][0]["kind"] == "zone_transition"

    switched, response = resolve_node_entry_event_runtime(travelling, event_key="next_zone_guard")

    assert response.screen.meta.zone_canvas_key == "chain_2x_grid_4x4_active_12"
    assert switched.current_zone_key == "z02"
    assert switched.zone_depth == 2
    assert switched.current_node_id == switched.start_node_id
    assert switched.visited_node_ids == {switched.start_node_id}
    assert switched.last_travel is not None
    assert switched.last_travel["zone_transition"] == {"from_zone_key": "z01", "to_zone_key": "z02"}
    assert switched.zone_chain["z01"]["node_events"][travelling.finish_node_id]["state"] == "cleared"


@pytest.mark.unit
def test_zone_runtime_uses_main_path_branch_graph_policy() -> None:
    runtime = _runtime(seed="maze-graph-check", void_cells=10)
    screen = build_rift_screen(runtime)
    open_node_ids = set(runtime.nodes) - runtime.void_node_ids
    runtime_edge_pairs = {
        tuple(sorted((edge.from_node_id, edge.to_node_id)))
        for edge in runtime.passage_edges.values()
    }
    debug_edge_pairs = {
        tuple(sorted((edge.from_node_id, edge.to_node_id)))
        for edge in screen.debug_map.passage_edges
    } if screen.debug_map else set()

    assert runtime.assembly_preset.get("graph_policy", {}).get("builder") == "main_path_branches"
    locked_targets = _locked_target_node_ids(runtime)
    guard_node_id = next(iter(runtime.node_events))
    assert _reachable(runtime, runtime.start_node_id) == open_node_ids - locked_targets
    assert locked_targets == {runtime.finish_node_id}
    assert len(open_node_ids) >= 12
    assert _edge_distance(runtime, runtime.start_node_id, guard_node_id) > 0
    assert _undirected_edge_count(runtime, state="open") == len(open_node_ids) - 2
    assert _undirected_edge_count(runtime, state="locked") == 1
    assert _undirected_edge_count(runtime, state="blocked_temporary") >= 1
    assert runtime.node_events
    assert runtime.gate_states
    assert screen.debug_map is not None
    assert debug_edge_pairs == runtime_edge_pairs
    assert any(edge.state == "blocked_temporary" for edge in screen.debug_map.passage_edges)
    assert any(edge.state == "locked" for edge in screen.debug_map.passage_edges)


@pytest.mark.unit
def test_rift_movement_uses_passage_edges_not_raw_adjacent_cells() -> None:
    runtime = _runtime(seed="edge-navigation-check", void_cells=10)
    screen = build_rift_screen(runtime)
    active_targets = {action.target_node_id for action in screen.movement if action.action == "move" and action.is_active}
    edge_targets = {
        edge.to_node_id
        for edge in runtime.passage_edges.values()
        if edge.from_node_id == runtime.current_node_id and edge.state == "open"
    }
    raw_open_neighbors = set(_open_neighbors(runtime, runtime.current_node_id))

    assert active_targets == edge_targets
    assert active_targets <= raw_open_neighbors
    assert any(edge.state == "blocked_temporary" for edge in runtime.passage_edges.values())


@pytest.mark.unit
def test_blocked_temporary_movement_uses_soft_blocker_contract() -> None:
    resources = RiftResourceLoader()
    setting = resources.load_setting("starter_rift")
    runtime = _runtime_with_temporary_blocker(seed_prefix="temporary-blocker-button-check")
    blocked_edge = next(edge for edge in runtime.passage_edges.values() if edge.state == "blocked_temporary")
    runtime = runtime.model_copy(
        update={
            "current_node_id": blocked_edge.from_node_id,
            "visited_node_ids": {blocked_edge.from_node_id},
            "previous_node_id": None,
        }
    )
    screen = build_rift_screen(runtime)
    action = next(item for item in screen.movement if item.target_node_id == blocked_edge.to_node_id)
    blocker = setting["blocker_vocabulary"]["soft_blocker"][0]

    assert action.state == "blocked_temporary"
    assert action.action == "inspect_blocker"
    assert action.is_active is True
    assert action.style == "primary"
    assert action.label == action.debug_text_parts["requirement"]["check"]["label"]
    assert not action.label.startswith(f"{blocker['button_label']} (")
    assert action.debug_text_parts["blocker_key"] == blocker["key"]
    assert len(action.debug_text_parts["requirements"]) == 1
    assert action.debug_text_parts["requirements"][0] in {"strength", "intelligence", "dexterity"}
    assert action.debug_text_parts["requirement"]["mode"] == "single_attribute"
    assert action.debug_text_parts["requirement"]["check"]["dc"] == 15
    assert action.debug_text_parts["requirement"]["check"]["key"] == action.debug_text_parts["requirements"][0]
    assert action.debug_text_parts["requirement_label"] not in action.label
    assert action.debug_text_parts["check_result"]["current_known"] is False
    assert action.debug_text_parts["check_result"]["can_pass"] is True
    assert "Требуется:" in action.tooltip
    assert action.debug_text_parts["interaction"]["mode"] == "single_attribute_check"
    assert action.debug_text_parts["interaction"]["resolved_checks"] == [action.debug_text_parts["requirement"]["check"]]


@pytest.mark.unit
def test_blocked_temporary_movement_disables_action_when_attribute_is_too_low() -> None:
    runtime = _runtime_with_temporary_blocker(seed_prefix="temporary-blocker-disabled-check")
    blocked_edge = next(edge for edge in runtime.passage_edges.values() if edge.state == "blocked_temporary")
    check = dict(blocked_edge.requirement["check"])
    runtime = runtime.model_copy(
        update={
            "current_node_id": blocked_edge.from_node_id,
            "visited_node_ids": {blocked_edge.from_node_id},
            "previous_node_id": None,
            "dev_character_snapshot": {"character": {"attributes": {check["key"]: check["dc"] - 2}}},
        }
    )

    screen = build_rift_screen(runtime)
    action = next(item for item in screen.movement if item.target_node_id == blocked_edge.to_node_id)

    assert action.action == "inspect_blocker"
    assert action.is_active is False
    assert action.style == "disabled"
    assert action.label == check["label"]
    assert action.debug_text_parts["check_result"]["current_known"] is True
    assert action.debug_text_parts["check_result"]["current_value"] == check["dc"] - 2
    assert action.debug_text_parts["check_result"]["shortfall"] == 2
    assert action.debug_text_parts["check_result"]["can_pass"] is False
    assert f"Требуется: {action.debug_text_parts['requirement_label']}" in action.tooltip
    assert f"У тебя: {check['dc'] - 2}" in action.tooltip
    assert "Не хватает: 2" in action.tooltip


@pytest.mark.unit
def test_blocked_temporary_movement_activates_action_when_attribute_is_high_enough() -> None:
    runtime = _runtime_with_temporary_blocker(seed_prefix="temporary-blocker-enabled-check")
    blocked_edge = next(edge for edge in runtime.passage_edges.values() if edge.state == "blocked_temporary")
    check = dict(blocked_edge.requirement["check"])
    runtime = runtime.model_copy(
        update={
            "current_node_id": blocked_edge.from_node_id,
            "visited_node_ids": {blocked_edge.from_node_id},
            "previous_node_id": None,
            "dev_character_snapshot": {"character": {"attributes": {check["key"]: check["dc"] + 1}}},
        }
    )

    screen = build_rift_screen(runtime)
    action = next(item for item in screen.movement if item.target_node_id == blocked_edge.to_node_id)

    assert action.action == "inspect_blocker"
    assert action.is_active is True
    assert action.style == "primary"
    assert action.label == check["label"]
    assert action.debug_text_parts["check_result"]["current_known"] is True
    assert action.debug_text_parts["check_result"]["current_value"] == check["dc"] + 1
    assert action.debug_text_parts["check_result"]["shortfall"] == 0
    assert action.debug_text_parts["check_result"]["can_pass"] is True
    assert f"Требуется: {action.debug_text_parts['requirement_label']}" in action.tooltip
    assert f"У тебя: {check['dc'] + 1}" in action.tooltip
    assert "Можно пройти" in action.tooltip


@pytest.mark.unit
def test_rift_action_resolves_temporary_blocker_when_attribute_check_passes() -> None:
    runtime = _runtime_with_temporary_blocker(seed_prefix="temporary-blocker-action-success-check")
    blocked_edge = next(edge for edge in runtime.passage_edges.values() if edge.state == "blocked_temporary")
    check = dict(blocked_edge.requirement["check"])
    runtime = runtime.model_copy(
        update={
            "current_node_id": blocked_edge.from_node_id,
            "visited_node_ids": {blocked_edge.from_node_id},
            "previous_node_id": None,
        }
    )

    updated, response = resolve_rift_action_runtime(
        runtime,
        RiftActionRequestDTO(
            action_type="resolve_blocker",
            target_node_id=blocked_edge.to_node_id,
            direction=blocked_edge.absolute_direction,
            payload={"attributes": {check["key"]: check["dc"]}},
        ),
    )

    assert response.action_type == "resolve_blocker"
    assert response.result == "success"
    assert response.details["check"]["key"] == check["key"]
    assert response.details["attribute_value"] == check["dc"]
    assert response.screen.current_node.node_id == blocked_edge.to_node_id
    assert updated.current_node_id == blocked_edge.to_node_id
    assert updated.previous_node_id == blocked_edge.from_node_id
    assert blocked_edge.to_node_id in updated.visited_node_ids
    assert updated.last_travel is not None
    assert updated.last_travel["from_node_id"] == blocked_edge.from_node_id
    assert updated.last_travel["to_node_id"] == blocked_edge.to_node_id
    assert updated.last_travel["suppress_random_node_combat"] is True
    assert updated.passage_edges[f"{blocked_edge.from_node_id}:{blocked_edge.absolute_direction}"].state == "open"
    assert updated.passage_edges[f"{blocked_edge.to_node_id}:{_opposite_direction(blocked_edge.absolute_direction)}"].state == "open"
    assert not any(action.target_node_id == blocked_edge.to_node_id for action in response.screen.movement)


@pytest.mark.unit
def test_rift_action_keeps_temporary_blocker_closed_when_attribute_check_fails() -> None:
    runtime = _runtime_with_temporary_blocker(seed_prefix="temporary-blocker-action-failure-check")
    blocked_edge = next(edge for edge in runtime.passage_edges.values() if edge.state == "blocked_temporary")
    check = dict(blocked_edge.requirement["check"])
    runtime = runtime.model_copy(
        update={
            "current_node_id": blocked_edge.from_node_id,
            "visited_node_ids": {blocked_edge.from_node_id},
            "previous_node_id": None,
        }
    )

    updated, response = resolve_rift_action_runtime(
        runtime,
        RiftActionRequestDTO(
            action_type="resolve_blocker",
            target_node_id=blocked_edge.to_node_id,
            direction=blocked_edge.absolute_direction,
            payload={"attributes": {check["key"]: check["dc"] - 1}},
        ),
    )

    assert response.action_type == "resolve_blocker"
    assert response.result == "failure"
    assert response.details["check"]["key"] == check["key"]
    assert response.details["attribute_value"] == check["dc"] - 1
    assert updated.passage_edges[f"{blocked_edge.from_node_id}:{blocked_edge.absolute_direction}"].state == "blocked_temporary"
    assert updated.passage_edges[f"{blocked_edge.to_node_id}:{_opposite_direction(blocked_edge.absolute_direction)}"].state == "blocked_temporary"


@pytest.mark.unit
def test_rift_action_uses_dev_character_snapshot_when_payload_has_no_attributes() -> None:
    runtime = _runtime_with_temporary_blocker(seed_prefix="temporary-blocker-action-snapshot-check")
    blocked_edge = next(edge for edge in runtime.passage_edges.values() if edge.state == "blocked_temporary")
    check = dict(blocked_edge.requirement["check"])
    runtime = runtime.model_copy(
        update={
            "current_node_id": blocked_edge.from_node_id,
            "visited_node_ids": {blocked_edge.from_node_id},
            "previous_node_id": None,
            "dev_character_snapshot": {
                "character": {
                    "attributes": {
                        check["key"]: check["dc"],
                    }
                }
            },
        }
    )

    updated, response = resolve_rift_action_runtime(
        runtime,
        RiftActionRequestDTO(
            action_type="resolve_blocker",
            target_node_id=blocked_edge.to_node_id,
            direction=blocked_edge.absolute_direction,
        ),
    )

    assert response.result == "success"
    assert response.details["attribute_value"] == check["dc"]
    assert updated.passage_edges[f"{blocked_edge.from_node_id}:{blocked_edge.absolute_direction}"].state == "open"


@pytest.mark.unit
def test_guard_node_event_unlocks_a_locked_passage_flag() -> None:
    runtime = _runtime(seed="guard-node-unlock-check", void_cells=10)
    guard_node_id, event = next(iter(runtime.node_events.items()))
    locked_edge = next(
        edge
        for edge in runtime.passage_edges.values()
        if edge.from_node_id == guard_node_id and edge.state == "locked"
    )
    runtime = runtime.model_copy(
        update={
            "current_node_id": guard_node_id,
            "visited_node_ids": {runtime.start_node_id, guard_node_id},
            "previous_node_id": None,
        }
    )
    screen = build_rift_screen(runtime)
    locked_action = next(action for action in screen.movement if action.target_node_id == locked_edge.to_node_id)

    assert locked_edge.to_node_id == runtime.finish_node_id
    assert runtime.nodes[locked_edge.to_node_id].pool_node_id == "starter_rift:015_rift_heart"
    assert screen.node_entry_event.state == "ready"
    assert screen.node_entry_event.event_type == "combat"
    assert screen.node_entry_event.event_key == "guard_combat"
    assert screen.node_entry_event.is_required is True
    assert screen.node_entry_event.grants_flags == event["grants_flags"]
    assert locked_action.state == "locked"
    assert locked_action.action == "none"
    with pytest.raises(ValueError, match="Target rift passage is not open"):
        start_travel_runtime(runtime, locked_edge.to_node_id)

    updated, response = resolve_node_entry_event_runtime(runtime, event_key="guard_combat")
    unlocked_screen = response.screen
    unlocked_action = next(action for action in unlocked_screen.movement if action.target_node_id == locked_edge.to_node_id)

    assert response.granted_flags == event["grants_flags"]
    assert set(response.granted_flags) <= updated.runtime_flags
    assert updated.node_events[guard_node_id]["state"] == "cleared"
    assert next(iter(updated.gate_states.values()))["state"] == "open"
    assert unlocked_screen.node_entry_event.state == "cleared"
    assert unlocked_action.state == "open"
    assert unlocked_action.action == "move"
    start_travel_runtime(updated, locked_edge.to_node_id)


@pytest.mark.unit
def test_random_reset_plan_can_ignore_default_scale_preset() -> None:
    resources = RiftResourceLoader()
    setting = resources.load_setting("starter_rift")
    scale_presets = resources.load_scale_presets()
    assembly_presets = resources.load_zone_assembly_presets()

    selected = {
        select_zone_assembly_plan(
            setting=setting,
            scale_presets=scale_presets,
            assembly_presets=assembly_presets,
            seed=f"reset-plan-{index}",
            use_default_scale=False,
        )[0]["preset_key"]
        for index in range(20)
    }

    assert "small" in selected
    assert "medium" in selected


@pytest.mark.unit
def test_rift_screen_builds_relative_buttons_from_neighbor_nodes() -> None:
    runtime = _runtime_with_transition_combat_move(seed_prefix="screen-check")
    screen = build_rift_screen(runtime)

    assert screen.current_node.node_id == runtime.start_node_id
    assert screen.hud.tier == 1
    assert screen.heart is not None
    assert screen.heart.status == "intact"
    assert screen.heart.tier == 1
    assert screen.heart.base_value == 100
    assert screen.heart.methods[0].method == "shatter"
    assert screen.heart.methods[0].enabled is True
    assert screen.exit.mode == "heart_exit_only"
    assert screen.exit.entrance_seals_on_entry is True
    assert screen.exit.can_leave is False
    assert screen.exit.can_complete is False
    assert screen.movement
    assert all(action.target_node_id for action in screen.movement if action.is_active)
    assert any(action.relative_direction == "forward" for action in screen.movement)
    assert all(action.travel for action in screen.movement if action.is_active and action.action == "move")
    assert any(action.travel and action.travel.duration_ms == 3000 for action in screen.movement if action.is_active)
    assert any(
        action.travel
        and action.travel.event_scope == "transition"
        and action.travel.tick_interval_ms == 1000
        and action.travel.event_check_count == 3
        and action.travel.possible_events == ["none", "combat"]
        for action in screen.movement
        if action.action == "move" and action.is_active
    )
    assert screen.node_entry_event.event_scope == "node_entry"
    assert screen.node_entry_event.state == "placeholder"
    assert screen.node_entry_event.possible_events == ["none", "combat"]
    assert screen.node_entry_event.combat_policy.random_combat_suppressed_by_transition_combat is True
    assert screen.node_entry_event.combat_policy.scripted_combat_suppresses_transition_combat is True
    assert "crystal_chamber" in screen.node_entry_event.combat_policy.scripted_combat_tags
    assert screen.radar.arms
    assert screen.map_view.center_node_id == runtime.start_node_id
    assert screen.map_view.current_coord == runtime.nodes[runtime.start_node_id].coord
    assert len(screen.map_view.visible_nodes) >= 2
    assert screen.map_view.visible_edges


@pytest.mark.unit
def test_rift_heart_shatter_records_mvp_reward_contract() -> None:
    runtime = _runtime(seed="heart-shatter-check", void_cells=5)
    runtime = runtime.model_copy(
        update={
            "current_node_id": runtime.finish_node_id,
            "visited_node_ids": {runtime.start_node_id, runtime.finish_node_id},
        }
    )

    updated, response = resolve_rift_action_runtime(
        runtime,
        RiftActionRequestDTO(action_type="resolve_heart", action_id="shatter"),
    )

    assert response.result == "success"
    assert response.details["heart"]["status"] == "shattered"
    assert response.details["heart"]["reward"] == {
        "lost_value": 50,
        "symbiote_xp": 25,
        "resource_value": 25,
        "resource_template_id": "currency_dust",
    }
    assert updated.heart_state["completion"]["status"] == "completed"
    assert response.screen.heart is not None
    assert response.screen.heart.can_exit is True
    assert response.screen.exit.can_complete is True
    assert response.screen.exit.actions[0].action == "complete_rift"
    assert response.screen.hud.objective is not None
    assert response.screen.hud.objective.is_complete is True


@pytest.mark.unit
def test_rift_return_to_exit_policy_hides_completion_until_exit_node() -> None:
    runtime = _runtime(seed="heart-return-to-exit-check", void_cells=5)
    runtime = runtime.model_copy(
        update={
            "setting": {
                **runtime.setting,
                "exit_policy": {
                    "mode": "heart_exit_only",
                    "completion_exit": "return_to_exit",
                    "exit_node_id": runtime.start_node_id,
                },
            },
            "current_node_id": runtime.finish_node_id,
            "visited_node_ids": {runtime.start_node_id, runtime.finish_node_id},
        }
    )

    updated, response = resolve_rift_action_runtime(
        runtime,
        RiftActionRequestDTO(action_type="resolve_heart", action_id="shatter"),
    )

    assert updated.heart_state["status"] == "shattered"
    assert response.screen.exit.completion_exit == "return_to_exit"
    assert response.screen.exit.exit_node_id == runtime.start_node_id
    assert response.screen.exit.can_complete is False
    assert response.screen.exit.reason == "return_to_exit_required"
    assert response.screen.exit.actions == []


@pytest.mark.unit
def test_rift_return_to_exit_policy_allows_completion_on_exit_node() -> None:
    runtime = _runtime(seed="heart-return-node-check", void_cells=5)
    runtime = runtime.model_copy(
        update={
            "setting": {
                **runtime.setting,
                "exit_policy": {
                    "mode": "heart_exit_only",
                    "completion_exit": "return_to_exit",
                    "exit_node_id": runtime.start_node_id,
                },
            },
            "current_node_id": runtime.start_node_id,
            "visited_node_ids": {runtime.start_node_id, runtime.finish_node_id},
            "heart_state": {
                **runtime.heart_state,
                "status": "shattered",
                "can_exit": True,
                "completion": {"status": "completed"},
            },
        }
    )

    screen = build_rift_screen(runtime)

    assert screen.exit.completion_exit == "return_to_exit"
    assert screen.exit.can_complete is True
    assert [action.action for action in screen.exit.actions] == ["complete_rift"]


@pytest.mark.unit
def test_rift_heart_shatter_requires_heart_node_metadata() -> None:
    runtime = _runtime(seed="heart-shatter-metadata-guard-check", void_cells=5)
    nodes = dict(runtime.nodes)
    heart_node = nodes[runtime.finish_node_id]
    nodes[runtime.finish_node_id] = heart_node.model_copy(
        update={
            "pool_node_id": "starter_rift:001_broken_milestone",
            "title": "Вход у разбитой вехи",
            "role_fit": ["start", "generic"],
            "tags": ["road", "starter_rift"],
        }
    )
    runtime = runtime.model_copy(
        update={
            "nodes": nodes,
            "current_node_id": runtime.finish_node_id,
            "visited_node_ids": {runtime.start_node_id, runtime.finish_node_id},
        }
    )

    with pytest.raises(ValueError, match="heart node metadata is invalid"):
        resolve_rift_action_runtime(
            runtime,
            RiftActionRequestDTO(action_type="resolve_heart", action_id="shatter"),
        )


@pytest.mark.unit
def test_scripted_target_node_suppresses_transition_combat_roll() -> None:
    runtime = _runtime(seed="scripted-node-suppression-check", void_cells=5)
    screen = build_rift_screen(runtime)
    scripted_keys = {"boss", "crystal_guard", "objective_gate", "story_combat", "key_combat", "crystal_chamber"}
    first_move = next(
        action
        for action in screen.movement
        if action.action == "move"
        and action.is_active
        and action.target_node_id
        and not set(runtime.nodes[action.target_node_id].role_fit).intersection(scripted_keys)
        and not set(runtime.nodes[action.target_node_id].tags).intersection(scripted_keys)
    )
    target_node_id = first_move.target_node_id or ""
    target_node = runtime.nodes[target_node_id]
    updated_nodes = dict(runtime.nodes)
    updated_nodes[target_node_id] = target_node.model_copy(update={"role_fit": [*target_node.role_fit, "boss"]})
    runtime = runtime.model_copy(update={"nodes": updated_nodes})

    updated_screen = build_rift_screen(runtime)
    action = next(item for item in updated_screen.movement if item.target_node_id == target_node_id)
    travelling, response = start_travel_runtime(runtime, target_node_id)

    assert action.travel is not None
    assert action.travel.suppressed_by_target_node_event is True
    assert action.travel.target_node_event_key == "boss"
    assert action.travel.can_trigger_event is False
    assert action.travel.possible_events == ["none"]
    assert travelling.active_travel is not None
    assert travelling.active_travel["suppressed_by_target_node_event"] is True
    assert travelling.active_travel["target_node_event_key"] == "boss"
    assert response.travel.suppressed_by_target_node_event is True
    assert response.travel.target_node_event_key == "boss"
    assert response.travel.checks_total == 3

    travel_id = response.travel.travel_id
    first_tick_runtime, first_tick = tick_travel_runtime(travelling, travel_id=travel_id, force_event="none")

    assert first_tick.travel.status == "moving"
    assert first_tick.travel.checks_done == 1
    assert first_tick.travel.remaining_ms == 2000
    assert first_tick_runtime.current_node_id == runtime.current_node_id

    second_tick_runtime, second_tick = tick_travel_runtime(first_tick_runtime, travel_id=travel_id, force_event="none")

    assert second_tick.travel.status == "moving"
    assert second_tick.travel.checks_done == 2
    assert second_tick.travel.remaining_ms == 1000
    assert second_tick_runtime.current_node_id == runtime.current_node_id

    completed_runtime, completed = tick_travel_runtime(second_tick_runtime, travel_id=travel_id, force_event="none")

    assert completed.travel.status == "completed"
    assert completed.travel.checks_done == 3
    assert completed.travel.remaining_ms == 0
    assert completed_runtime.current_node_id == target_node_id


@pytest.mark.unit
def test_crystal_chamber_scripted_node_is_seeded_as_required_entry_combat() -> None:
    runtime = _runtime(seed="crystal-chamber-scripted-event-check", void_cells=5)
    event = runtime.node_events[runtime.finish_node_id]

    assert event["event_key"] == "crystal_chamber"
    assert event["event_type"] == "combat"
    assert event["state"] == "ready"
    assert event["source"] == "scripted_node"
    assert event["is_required"] is True
    assert event["encounter_kind"] == "heart_guard"
    assert runtime.node_states[runtime.finish_node_id]["entry_event_state"] == "ready"
    assert runtime.node_states[runtime.finish_node_id]["event_key"] == "crystal_chamber"


@pytest.mark.unit
def test_scripted_node_entry_combat_returns_prompt_after_travel_completion() -> None:
    runtime = _runtime(seed="scripted-node-entry-prompt-check", void_cells=5)
    guard_node_id = next(node_id for node_id, event in runtime.node_events.items() if event.get("event_key") == "guard_combat")
    unlocked, _response = resolve_node_entry_event_runtime(
        runtime.model_copy(
            update={
                "current_node_id": guard_node_id,
                "visited_node_ids": {runtime.start_node_id, guard_node_id},
            }
        ),
        event_key="guard_combat",
    )

    travelling, response = start_travel_runtime(unlocked, unlocked.finish_node_id)
    completed = response
    while completed.travel.status == "moving":
        travelling, completed = tick_travel_runtime(travelling, travel_id=response.travel.travel_id, force_event="none")

    assert travelling.current_node_id == unlocked.finish_node_id
    assert completed.travel.status == "completed"
    assert completed.combat_prompt is not None
    assert completed.combat_prompt.metadata["event_scope"] == "node_entry"
    assert completed.combat_prompt.metadata["event_key"] == "crystal_chamber"
    assert completed.combat_prompt.metadata["encounter_kind"] == "heart_guard"
    assert completed.screen is None


@pytest.mark.unit
def test_ordinary_node_roll_creates_node_entry_combat_after_travel_completion() -> None:
    runtime = _runtime_with_forced_ordinary_combat(seed="ordinary-node-entry-combat-check")
    with use_tunables(DEFAULT_RIFT_FORCED_ORDINARY_COMBAT):
        screen = build_rift_screen(runtime)
        first_move = next(
            action
            for action in screen.movement
            if action.action == "move" and action.is_active and action.target_node_id and action.travel
            and action.target_node_id not in runtime.node_events
            and "combat" in action.travel.possible_events
        )

        moved = _complete_travel(runtime, first_move.target_node_id or "")
        moved_screen = build_rift_screen(moved)

    assert moved.current_node_id == first_move.target_node_id
    assert moved.last_travel is not None
    assert moved.last_travel["event_type"] == "none"
    assert moved.last_travel["suppress_random_node_combat"] is False
    assert moved_screen.node_entry_event.state == "ready"
    assert moved_screen.node_entry_event.event_type == "combat"
    assert moved_screen.node_entry_event.event_key == "ordinary_combat"
    assert moved_screen.node_entry_event.is_required is False
    assert moved_screen.node_entry_event.title == f"Стычка: {moved.nodes[moved.current_node_id].title}"
    assert "помещ" not in (moved_screen.node_entry_event.title or "").lower()
    assert "комнат" not in (moved_screen.node_entry_event.description or "").lower()
    assert moved_screen.node_entry_event.metadata["source"] == "ordinary_roll"
    assert moved.node_states[moved.current_node_id]["ordinary_event_state"] == "ready"
    assert moved.node_events[moved.current_node_id]["source"] == "ordinary_roll"


@pytest.mark.unit
def test_ordinary_node_entry_combat_returns_combat_prompt_after_travel_completion() -> None:
    runtime = _runtime_with_forced_ordinary_combat(seed="ordinary-node-entry-combat-check")
    with use_tunables(DEFAULT_RIFT_FORCED_ORDINARY_COMBAT):
        screen = build_rift_screen(runtime)
        first_move = next(
            action
            for action in screen.movement
            if action.action == "move" and action.is_active and action.target_node_id and action.travel
            and action.target_node_id not in runtime.node_events
            and action.target_node_id not in runtime.visited_node_ids
            and "combat" in action.travel.possible_events
        )
        travelling, response = start_travel_runtime(runtime, first_move.target_node_id or "")

        completed = response
        moved = travelling
        while completed.travel.status == "moving":
            moved, completed = tick_travel_runtime(moved, travel_id=response.travel.travel_id, force_event="none")

    assert completed.travel.status == "completed"
    assert completed.combat_prompt is not None
    assert completed.combat_prompt.metadata["event_scope"] == "node_entry"
    assert completed.combat_prompt.metadata["event_key"] == "ordinary_combat"
    assert completed.combat_prompt.metadata["encounter_kind"] == "ordinary_node"
    assert completed.screen is None
    assert moved.node_events[moved.current_node_id]["is_required"] is False


@pytest.mark.unit
def test_ordinary_node_entry_does_not_roll_loot_before_combat() -> None:
    base_runtime = _runtime(seed="ordinary-node-entry-no-precombat-loot", void_cells=8)
    with use_tunables(DEFAULT_RIFT_NO_ORDINARY_COMBAT):
        screen = build_rift_screen(base_runtime)
        first_move = next(
            action
            for action in screen.movement
            if action.action == "move" and action.is_active and action.target_node_id and action.travel
            and action.travel.possible_events == ["none", "combat"]
            and action.target_node_id not in base_runtime.node_events
            and action.target_node_id not in base_runtime.visited_node_ids
        )

        moved = _complete_travel(base_runtime, first_move.target_node_id or "")
        moved_screen = build_rift_screen(moved)

    assert moved_screen.node_entry_event.event_type == "none"
    assert moved.current_node_id not in moved.node_events
    assert moved.node_states[moved.current_node_id]["ordinary_event_type"] == "none"
    assert moved.node_states[moved.current_node_id]["ordinary_event_state"] == "resolved"


@pytest.mark.unit
def test_transition_combat_suppresses_ordinary_node_combat_roll_on_arrival() -> None:
    runtime = _runtime_with_forced_ordinary_combat(seed="ordinary-node-entry-suppressed-check")
    with use_tunables(DEFAULT_RIFT_FORCED_ORDINARY_COMBAT):
        screen = build_rift_screen(runtime)
        first_move = next(
            action
            for action in screen.movement
            if action.action == "move" and action.is_active and action.target_node_id and action.travel
            and action.target_node_id not in runtime.node_events
            and "combat" in action.travel.possible_events
        )
        travelling, response = start_travel_runtime(runtime, first_move.target_node_id or "")
        travel_id = response.travel.travel_id
        travelling, response = tick_travel_runtime(travelling, travel_id=travel_id, force_event="combat")

        moved, resolved = resolve_transition_combat_runtime(travelling, travel_id=travel_id)
        moved_screen = resolved.screen

    assert response.travel.status == "interrupted"
    assert moved.current_node_id == first_move.target_node_id
    assert moved.last_travel is not None
    assert moved.last_travel["event_type"] == "combat"
    assert moved.last_travel["suppress_random_node_combat"] is True
    assert moved_screen.node_entry_event.event_type == "none"
    assert moved_screen.node_entry_event.state == "placeholder"
    assert moved.current_node_id not in moved.node_events
    assert moved.node_states[moved.current_node_id]["ordinary_event_state"] == "suppressed"


@pytest.mark.unit
def test_rift_map_view_returns_current_node_neighbors_and_edges() -> None:
    runtime = _runtime(seed="map-view-check", void_cells=10)
    screen = build_rift_screen(runtime)

    node_ids = {node.node_id for node in screen.map_view.visible_nodes}
    edge_targets = {edge.to_node_id for edge in screen.map_view.visible_edges if edge.to_node_id}

    assert runtime.current_node_id in node_ids
    assert edge_targets <= node_ids
    assert all(edge.from_node_id == runtime.current_node_id for edge in screen.map_view.visible_edges)
    assert {node.state for node in screen.map_view.visible_nodes} <= {"current", "open", "blocked_temporary"}
    assert {edge.state for edge in screen.map_view.visible_edges} <= {
        "open",
        "blocked_temporary",
    }


@pytest.mark.unit
def test_void_surroundings_use_setting_boundary_descriptors() -> None:
    resources = RiftResourceLoader()
    setting = resources.load_setting("starter_rift")
    runtime = _runtime(seed="void-descriptor-check", void_cells=10)
    void_coord_keys = {coord_key(coord.x, coord.y) for coord in runtime.void_coords}
    current_node_id = next(
        node_id
        for node_id, node in runtime.nodes.items()
        if any(
            coord_key(neighbor_coord(node.coord, direction).x, neighbor_coord(node.coord, direction).y) in void_coord_keys
            for direction in ORDERED_DIRECTIONS
        )
    )
    runtime = runtime.model_copy(
        update={
            "current_node_id": current_node_id,
            "visited_node_ids": {current_node_id},
            "previous_node_id": None,
        }
    )
    screen = build_rift_screen(runtime)
    descriptors = setting["blocker_vocabulary"]["void_surface_descriptors"]
    narrative_lines = {line for descriptor in descriptors for line in descriptor["narrative_lines"]}
    button_labels = {label for descriptor in descriptors for label in descriptor["button_labels"]}

    assert any(
        surrounding.state == "void" and any(line in surrounding.text for line in narrative_lines)
        for surrounding in screen.surroundings
    )
    assert button_labels
    assert all(action.state != "void" for action in screen.movement)


@pytest.mark.unit
def test_rift_travel_completion_updates_heading_and_back_button() -> None:
    runtime = _runtime(seed="move-check", void_cells=5)
    screen = build_rift_screen(runtime)
    first_move = next(
        action
        for action in screen.movement
        if action.action == "move" and action.is_active and action.target_node_id
    )

    moved = _complete_travel(runtime, first_move.target_node_id or "")
    next_screen = build_rift_screen(moved)

    assert moved.previous_node_id == runtime.current_node_id
    assert moved.current_node_id == first_move.target_node_id
    assert moved.last_travel
    assert moved.last_travel["kind"] == "exploration"
    assert moved.last_travel["duration_ms"] == 3000
    assert moved.last_travel["event_scope"] == "transition"
    assert moved.last_travel["event_type"] == "none"
    assert any(action.relative_direction == "back" for action in next_screen.movement)
    assert any(
        action.relative_direction == "back"
        and action.travel
        and action.travel.duration_ms == 1000
        and action.travel.event_check_count == 0
        and action.travel.possible_events == ["none"]
        for action in next_screen.movement
    )


@pytest.mark.unit
def test_rift_rebuild_regenerates_zone_state_without_replacing_pool_cells() -> None:
    runtime = _runtime(seed="rebuild-before", void_cells=5)
    screen = build_rift_screen(runtime)
    first_move = next(
        action
        for action in screen.movement
        if action.action == "move" and action.is_active and action.target_node_id
    )
    moved = _complete_travel(runtime, first_move.target_node_id or "")
    original_placements = [(item.cell_id, item.x, item.y, item.pool_node_id) for item in moved.placements]
    original_pool_by_cell = {node_id: node.pool_node_id for node_id, node in moved.nodes.items()}

    rebuilt = rebuild_zone_state(moved, seed="rebuild-after", void_cells=10)

    assert [(item.cell_id, item.x, item.y, item.pool_node_id) for item in rebuilt.placements] == original_placements
    assert {node_id: node.pool_node_id for node_id, node in rebuilt.nodes.items()} == original_pool_by_cell
    assert rebuilt.current_node_id == moved.current_node_id
    assert rebuilt.visited_node_ids == moved.visited_node_ids
    assert rebuilt.last_travel is None
    assert not ({rebuilt.start_node_id, rebuilt.finish_node_id, rebuilt.current_node_id} & rebuilt.void_node_ids)
    assert rebuilt.finish_node_id in _reachable(rebuilt, rebuilt.start_node_id)
    assert rebuilt.finish_node_id in _reachable(rebuilt, rebuilt.current_node_id)


def _runtime(*, seed: str, void_cells: int) -> RiftZoneRuntimeDTO:
    resources = RiftResourceLoader()
    scale_presets = resources.load_scale_presets()
    assembly_presets = resources.load_zone_assembly_presets()
    pool_nodes = resources.load_node_pool("starter_rift")
    required_nodes = max(15, 25 - void_cells)
    return build_zone_runtime(
        setting=resources.load_setting("starter_rift"),
        pool_nodes=_expanded_pool_nodes(pool_nodes, target=required_nodes),
        scale_preset=scale_presets["medium"],
        assembly_preset=assembly_presets["grid_5x5_active_15"],
        seed=seed,
        void_cells=void_cells,
        debug=True,
    )


def _expanded_pool_nodes(pool_nodes: dict, *, target: int) -> dict:
    nodes = dict(pool_nodes)
    source_nodes = list(pool_nodes.values())
    index = 0
    while len(nodes) < target:
        source = source_nodes[index % len(source_nodes)]
        copy_id = f"{source.pool_node_id}:copy_{index}"
        nodes[copy_id] = source.model_copy(update={"pool_node_id": copy_id, "pool_order": len(nodes)})
        index += 1
    return nodes


def _runtime_with_temporary_blocker(*, seed_prefix: str) -> RiftZoneRuntimeDTO:
    for index in range(20):
        runtime = _runtime(seed=f"{seed_prefix}-{index}", void_cells=10)
        if any(edge.state == "blocked_temporary" for edge in runtime.passage_edges.values()):
            return runtime
    raise AssertionError("Expected at least one deterministic runtime with a temporary blocker")


def _runtime_with_transition_combat_move(*, seed_prefix: str) -> RiftZoneRuntimeDTO:
    for index in range(20):
        runtime = _runtime(seed=f"{seed_prefix}-{index}", void_cells=5)
        screen = build_rift_screen(runtime)
        if any(
            action.action == "move"
            and action.is_active
            and action.travel
            and action.travel.possible_events == ["none", "combat"]
            for action in screen.movement
        ):
            return runtime
    raise AssertionError("Expected at least one deterministic runtime with a transition combat move")


def _runtime_with_forced_ordinary_combat(*, seed: str) -> RiftZoneRuntimeDTO:
    for index in range(20):
        runtime = _runtime(seed=f"{seed}-{index}", void_cells=5)
        with use_tunables(DEFAULT_RIFT_FORCED_ORDINARY_COMBAT):
            screen = build_rift_screen(runtime)
            if any(
                action.action == "move"
                and action.is_active
                and action.target_node_id
                and action.travel
                and action.target_node_id not in runtime.node_events
                and "combat" in action.travel.possible_events
                for action in screen.movement
            ):
                return runtime
    raise AssertionError("Expected at least one deterministic runtime with an ordinary combat move")


DEFAULT_RIFT_FORCED_ORDINARY_COMBAT = RiftTunables(ordinary_node_combat_chance=1.0)
DEFAULT_RIFT_NO_ORDINARY_COMBAT = RiftTunables(ordinary_node_combat_chance=0.0)


def _complete_travel(runtime: RiftZoneRuntimeDTO, target_node_id: str) -> RiftZoneRuntimeDTO:
    travelling, response = start_travel_runtime(runtime, target_node_id)
    travel_id = response.travel.travel_id
    for _ in range(max(1, response.travel.checks_total)):
        travelling, response = tick_travel_runtime(travelling, travel_id=travel_id, force_event="none")
    assert response.travel.status == "completed"
    return travelling


def _reachable(runtime: RiftZoneRuntimeDTO, start_node_id: str) -> set[str]:
    queue: deque[str] = deque([start_node_id])
    seen: set[str] = set()
    while queue:
        node_id = queue.popleft()
        if node_id in seen or node_id in runtime.void_node_ids:
            continue
        seen.add(node_id)
        for edge in runtime.passage_edges.values():
            if edge.from_node_id == node_id and edge.state == "open" and edge.to_node_id not in seen:
                queue.append(edge.to_node_id)
    return seen


def _open_neighbors(runtime: RiftZoneRuntimeDTO, node_id: str) -> list[str]:
    node = runtime.nodes[node_id]
    result: list[str] = []
    for direction in ORDERED_DIRECTIONS:
        neighbor = neighbor_coord(node.coord, direction)
        target_node_id = runtime.cells_by_coord.get(coord_key(neighbor.x, neighbor.y))
        if target_node_id and target_node_id not in runtime.void_node_ids:
            result.append(target_node_id)
    return result


def _edge_distance(runtime: RiftZoneRuntimeDTO, start_node_id: str, finish_node_id: str) -> int:
    queue: deque[tuple[str, int]] = deque([(start_node_id, 0)])
    seen: set[str] = set()
    while queue:
        node_id, distance = queue.popleft()
        if node_id == finish_node_id:
            return distance
        if node_id in seen:
            continue
        seen.add(node_id)
        for edge in runtime.passage_edges.values():
            if edge.from_node_id == node_id and edge.state == "open" and edge.to_node_id not in seen:
                queue.append((edge.to_node_id, distance + 1))
    return -1


def _open_path(runtime: RiftZoneRuntimeDTO, start_node_id: str, finish_node_id: str) -> list[str]:
    queue: deque[str] = deque([start_node_id])
    parent: dict[str, str | None] = {start_node_id: None}
    while queue:
        node_id = queue.popleft()
        if node_id == finish_node_id:
            break
        for edge in runtime.passage_edges.values():
            if edge.from_node_id == node_id and edge.state == "open" and edge.to_node_id not in parent:
                parent[edge.to_node_id] = node_id
                queue.append(edge.to_node_id)
    if finish_node_id not in parent:
        raise AssertionError(f"Expected open path from {start_node_id} to {finish_node_id}")
    result = [finish_node_id]
    current = finish_node_id
    while parent[current] is not None:
        current = parent[current] or ""
        result.append(current)
    result.reverse()
    return result


def _open_path_effective(runtime: RiftZoneRuntimeDTO, start_node_id: str, finish_node_id: str) -> list[str]:
    queue: deque[str] = deque([start_node_id])
    parent: dict[str, str | None] = {start_node_id: None}
    while queue:
        node_id = queue.popleft()
        if node_id == finish_node_id:
            break
        for edge in runtime.passage_edges.values():
            if (
                edge.from_node_id == node_id
                and _effective_edge_state_for_test(runtime, edge) == "open"
                and edge.to_node_id not in parent
            ):
                parent[edge.to_node_id] = node_id
                queue.append(edge.to_node_id)
    if finish_node_id not in parent:
        raise AssertionError(f"Expected effective open path from {start_node_id} to {finish_node_id}")
    result = [finish_node_id]
    current = finish_node_id
    while parent[current] is not None:
        current = parent[current] or ""
        result.append(current)
    result.reverse()
    return result


def _reachable_effective(runtime: RiftZoneRuntimeDTO, start_node_id: str) -> set[str]:
    queue: deque[str] = deque([start_node_id])
    seen: set[str] = set()
    while queue:
        node_id = queue.popleft()
        if node_id in seen or node_id in runtime.void_node_ids:
            continue
        seen.add(node_id)
        for edge in runtime.passage_edges.values():
            if (
                edge.from_node_id == node_id
                and _effective_edge_state_for_test(runtime, edge) == "open"
                and edge.to_node_id not in seen
            ):
                queue.append(edge.to_node_id)
    return seen


def _effective_edge_state_for_test(runtime: RiftZoneRuntimeDTO, edge) -> str:
    requirement = dict(edge.requirement or {})
    if (
        edge.state in {"locked", "blocked_temporary"}
        and requirement.get("type") == "rift_flag"
        and str(requirement.get("flag") or "") in runtime.runtime_flags
    ):
        return "open"
    return edge.state


def _undirected_edge_count(runtime: RiftZoneRuntimeDTO, *, state: str) -> int:
    pairs = {
        tuple(sorted((edge.from_node_id, edge.to_node_id)))
        for edge in runtime.passage_edges.values()
        if edge.state == state
    }
    return len(pairs)


def _locked_target_node_ids(runtime: RiftZoneRuntimeDTO) -> set[str]:
    result: set[str] = set()
    for gate_state in runtime.gate_states.values():
        target_node_id = gate_state.get("to_node_id")
        if isinstance(target_node_id, str):
            result.add(target_node_id)
    return result


def _opposite_direction(direction: str) -> str:
    return {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
    }[direction]
