from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.world.prompts.router import build_batch_location_desc
from src.backend.features.world.resources.static.start_village import STATIC_LOCATIONS
from src.backend.features.world.loaders.village_loader import VillageLoader
from src.backend.features.world.services.generator_service import LLMWorldGenerator
from src.backend.features.world.services.navigation_service import WorldNavigationService


class FakeGenerationAI:
    def __init__(self) -> None:
        self.specs = None

    async def enqueue_many(self, specs):
        self.specs = list(specs)
        return SimpleNamespace(batch_id="batch-1", created=len(self.specs), reused=0, scheduled=len(self.specs))


def _runtime_node_map(raw_nodes: list[dict]) -> dict[str, SimpleNamespace]:
    return {
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


def _runtime_nav_degrees(raw_nodes: list[dict]) -> dict[str, int]:
    navigation = WorldNavigationService()
    node_map = _runtime_node_map(raw_nodes)
    return {
        loc_id: sum(1 for key in navigation.calculate_exits(node, node_map) if key.startswith("nav:"))
        for loc_id, node in node_map.items()
    }


def _is_four_way_exempt(raw_node: dict) -> bool:
    flags = raw_node.get("flags", {})
    return bool(isinstance(flags, dict) and (flags.get("is_safe_zone") or flags.get("is_gate")))


def _non_exempt_four_way_nodes(raw_nodes: list[dict]) -> dict[str, int]:
    raw_by_loc = {f"{raw['x']}_{raw['y']}": raw for raw in raw_nodes}
    return {
        loc_id: degree
        for loc_id, degree in _runtime_nav_degrees(raw_nodes).items()
        if degree >= 4 and not _is_four_way_exempt(raw_by_loc[loc_id])
    }


def _reachable_locs(raw_nodes: list[dict], *, start: str) -> set[str]:
    navigation = WorldNavigationService()
    node_map = _runtime_node_map(raw_nodes)
    visited = {start}
    queue = [start]
    while queue:
        current = queue.pop(0)
        for key in navigation.calculate_exits(node_map[current], node_map):
            if not key.startswith("nav:"):
                continue
            target = key.removeprefix("nav:")
            if target not in visited:
                visited.add(target)
                queue.append(target)
    return visited


@pytest.mark.unit
async def test_generate_world_shell_uses_anchor_influence():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    generator = LLMWorldGenerator(data, generation_ai=None)

    await generator._generate_world_shell()

    assert data.upsert_region.await_count == 49
    assert data.upsert_zone.await_count == 441

    zones = {call.args[0]: call.kwargs for call in data.upsert_zone.await_args_list}
    north_zone = zones["A1_1_1"]
    d4_center_zone = zones["D4_1_1"]
    first_ring_zone = zones["C4_1_1"]

    assert north_zone["biome_id"] == "mountains"
    assert north_zone["flags"]["dominant_anchor"] == "north_prime"
    assert north_zone["flags"]["anomaly_id"] == "stasis"
    assert north_zone["flags"]["anchor_tags"]
    assert north_zone["navigation_profile_id"] == "mountain_passes"
    assert north_zone["zone_archetype"] == "mountains_core"
    assert d4_center_zone["tier"] == 0
    assert d4_center_zone["biome_id"] == "city_ruins"
    assert d4_center_zone["flags"]["is_inside_city_shield"] is True
    assert d4_center_zone["zone_archetype"] == "safe_hub"
    assert first_ring_zone["flags"]["is_locked_frontier"] is True
    assert first_ring_zone["population_tags"]


@pytest.mark.unit
async def test_generate_d4_capital_creates_first_playable_territory():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    data.bulk_upsert_nodes = AsyncMock()
    data.flush = AsyncMock()
    data.get_nodes_in_rect = AsyncMock(return_value=[])
    generator = LLMWorldGenerator(data, generation_ai=None)

    await generator._generate_d4_capital()

    data.upsert_region.assert_awaited_once()
    assert data.upsert_zone.await_count == 9
    zones = {call.args[0]: call.kwargs for call in data.upsert_zone.await_args_list}
    assert zones["D4_1_1"]["tier"] == 0
    assert zones["D4_1_1"]["biome_id"] == "city_ruins"
    assert zones["D4_1_1"]["zone_archetype"] == "safe_hub"
    assert zones["D4_1_1"]["flags"]["is_safe_zone"] is True
    assert zones["D4_0_0"]["tier"] == 1
    assert zones["D4_0_0"]["flags"]["threat_tier"] == 1
    assert zones["D4_0_0"]["flags"]["anchor_influence"]
    assert zones["D4_0_0"]["zone_archetype"] == "corner_rift_district"
    assert zones["D4_0_0"]["navigation_profile_id"] == "city_ruins_labyrinth"
    assert zones["D4_0_0"]["population_tags"] == ["d4_corner_pressure"]
    data.flush.assert_awaited_once()
    data.bulk_upsert_nodes.assert_awaited_once()

    nodes = data.bulk_upsert_nodes.await_args.args[0]
    assert len(nodes) == 225
    assert {node["zone_id"] for node in nodes} == {f"D4_{zx}_{zy}" for zx in range(3) for zy in range(3)}

    by_coord = {(node["x"], node["y"]): node for node in nodes}
    assert by_coord[(52, 52)]["flags"]["is_safe_zone"] is True
    assert by_coord[(52, 52)]["movement_profile"]["has_road"] is True
    assert by_coord[(52, 52)]["node_type"] == "hub"
    assert by_coord[(52, 52)]["navigation_profile_id"] == "city_ruins_labyrinth"
    assert by_coord[(48, 56)]["flags"]["is_safe_zone"] is False
    assert by_coord[(48, 56)]["flags"]["threat_tier"] == 1
    assert by_coord[(48, 56)]["flags"]["anchor_influence"]["threat"] == pytest.approx(0.03)
    assert "d4_corner_pressure" in by_coord[(48, 56)]["flags"]["context_tags"]
    assert by_coord[(48, 56)]["node_type"] in {"buildable_plot", "ruined_quarter"}
    assert by_coord[(48, 56)]["movement_profile"]["zone_archetype"] == "corner_rift_district"
    assert "former capital" in by_coord[(48, 56)]["flags"]["narrative_context"]
    assert "former_capital_ruins" in by_coord[(48, 56)]["content"]["environment_tags"]
    assert by_coord[(52, 45)]["flags"]["threat_tier"] == 0
    assert by_coord[(52, 45)]["node_type"] == "sealed_gate"
    assert by_coord[(52, 45)]["landmark_profile"] == "sealed_city_gate"
    assert "d4_tier0_gate_cross" in by_coord[(52, 45)]["flags"]["context_tags"]
    assert by_coord[(46, 46)]["node_type"] == "rift"
    assert by_coord[(46, 46)]["flags"]["threat_tier"] == 2
    assert by_coord[(46, 46)]["flags"]["rift_profile"]["family_id"] == "rat_swarm"
    assert "d4_rift_rat_king" in by_coord[(46, 46)]["content"]["environment_tags"]
    assert by_coord[(45, 45)]["terrain_type"] == "outer_monolith_wall_walk"
    assert by_coord[(45, 45)]["node_type"] == "outer_wall_walk"
    assert by_coord[(45, 45)]["flags"]["is_passable"] is True
    assert set(by_coord[(45, 45)]["movement_profile"]["blocked_exits"]) == {"north", "west"}
    assert by_coord[(45, 46)]["movement_profile"]["blocked_exits"] == ["west"]

    gates = [node for node in nodes if node["flags"].get("is_gate")]
    assert {(gate["x"], gate["y"]) for gate in gates} == {(52, 45), (52, 59), (45, 52), (59, 52)}
    assert {gate["flags"]["gate_direction"] for gate in gates} == {"north", "south", "west", "east"}
    assert all(gate["flags"]["exit_locked"] is True for gate in gates)
    assert all(
        gate["movement_profile"]["gated_exits"][gate["flags"]["gate_direction"]]["state"] == "locked"
        for gate in gates
    )


@pytest.mark.unit
async def test_generate_d4_capital_movement_profile_keeps_all_nodes_reachable():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    data.bulk_upsert_nodes = AsyncMock()
    data.flush = AsyncMock()
    data.get_nodes_in_rect = AsyncMock(return_value=[])
    generator = LLMWorldGenerator(data, generation_ai=None)

    await generator._generate_d4_capital()

    raw_nodes = data.bulk_upsert_nodes.await_args.args[0]
    visited = _reachable_locs(raw_nodes, start="52_52")

    assert visited == set(_runtime_node_map(raw_nodes))


@pytest.mark.unit
async def test_generate_d4_capital_has_no_four_way_navigation_nodes_outside_safe_zone_and_gates():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    data.bulk_upsert_nodes = AsyncMock()
    data.flush = AsyncMock()
    data.get_nodes_in_rect = AsyncMock(return_value=[])
    generator = LLMWorldGenerator(data, generation_ai=None)

    await generator._generate_d4_capital()

    raw_nodes = data.bulk_upsert_nodes.await_args.args[0]
    assert _non_exempt_four_way_nodes(raw_nodes) == {}


@pytest.mark.unit
async def test_d4_static_seed_has_no_four_way_navigation_nodes_outside_safe_zone_and_gates():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    data.bulk_upsert_nodes = AsyncMock()
    data.flush = AsyncMock()
    data.get_nodes_in_rect = AsyncMock(return_value=[])
    generator = LLMWorldGenerator(data, generation_ai=None)

    await generator._generate_d4_capital()
    generated_nodes = data.bulk_upsert_nodes.await_args.args[0]

    village_data = MagicMock()
    village_data.region_exists = AsyncMock(return_value=True)
    village_data.get_zone = AsyncMock(return_value=True)
    village_data.bulk_upsert_nodes = AsyncMock()
    await VillageLoader(village_data).load_village(STATIC_LOCATIONS)
    village_nodes = village_data.bulk_upsert_nodes.await_args.args[0]

    by_coord = {(node["x"], node["y"]): node for node in generated_nodes}
    by_coord.update({(node["x"], node["y"]): node for node in village_nodes})
    raw_nodes = list(by_coord.values())
    assert _non_exempt_four_way_nodes(raw_nodes) == {}
    assert _reachable_locs(raw_nodes, start="52_52") == set(_runtime_node_map(raw_nodes))


@pytest.mark.unit
async def test_generate_d4_capital_preserves_enriched_non_static_content():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    data.bulk_upsert_nodes = AsyncMock()
    data.flush = AsyncMock()
    data.get_nodes_in_rect = AsyncMock(
        return_value=[
            MagicMock(
                x=48,
                y=56,
                content={
                    "title": "Пепельный Двор",
                    "description": "AI описание квартала.",
                    "environment_tags": ["custom_ai_tag"],
                },
            ),
            MagicMock(
                x=49,
                y=56,
                content={
                    "title": "Руины Старой Столицы",
                    "description": (
                        "Мертвый квартал древней столицы. Координата описывает не размер, а отдельную "
                        "навигационную область: улицу, площадь, двор или фрагмент квартала."
                    ),
                    "environment_tags": ["old_fallback_tag"],
                },
            ),
        ]
    )
    generator = LLMWorldGenerator(data, generation_ai=None)

    await generator._generate_d4_capital()

    nodes = data.bulk_upsert_nodes.await_args.args[0]
    by_coord = {(node["x"], node["y"]): node for node in nodes}
    assert by_coord[(48, 56)]["content"]["title"] == "Пепельный Двор"
    assert by_coord[(48, 56)]["content"]["description"] == "AI описание квартала."
    assert by_coord[(49, 56)]["content"]["title"] == "Руины Старой Столицы"
    assert by_coord[(49, 56)]["content"]["environment_tags"] != ["old_fallback_tag"]


def test_static_inner_city_gates_are_safe_locations():
    inner_gate_coords = {(52, 50), (52, 54), (50, 52), (54, 52)}

    assert all(STATIC_LOCATIONS[coord]["flags"]["is_safe_zone"] is True for coord in inner_gate_coords)


@pytest.mark.unit
async def test_run_test_mode_generates_d4_then_loads_static_hub():
    data = MagicMock()
    data.upsert_region = AsyncMock()
    data.upsert_zone = AsyncMock()
    data.bulk_upsert_nodes = AsyncMock()
    data.flush = AsyncMock()
    data.get_nodes_in_rect = AsyncMock(return_value=[])
    data.region_exists = AsyncMock(return_value=True)
    data.get_zone = AsyncMock(return_value=True)
    generator = LLMWorldGenerator(data, generation_ai=None)
    generator.village_loader.load_village = AsyncMock()

    await generator.run("test")

    data.bulk_upsert_nodes.assert_awaited_once()
    generator.village_loader.load_village.assert_awaited_once()


@pytest.mark.unit
async def test_batch_location_desc_prompt_uses_typed_district_contract():
    result = await build_batch_location_desc(
        [
            {
                "id": "45_52",
                "tags": ["ancient_city", "city_ruins", "city_ruins_edge", "gate", "road"],
                "context": ["На востоке виднеется ancient_highway"],
                "district_context": {
                    "name": "Северный тракт и ворота",
                    "role": "main road to the sealed northern gate",
                    "tags": ["north_gate", "ancient_highway"],
                },
            }
        ]
    )

    system = result.messages[0].content
    user = result.messages[1].content

    assert "batch_location_desc" not in system
    assert "ROLE: Narrative Designer for 'Echo of Ancients'" in system
    assert "tags" in user
    assert "context" in user
    assert "district_context" in user
    assert "45_52" in user
    assert result.max_tokens == 5000
    assert result.temperature == 0.7
    assert "up to 5 nearby locations" in system
    assert "locations array" in system
    assert "route_context" in system
    assert "Boundary tags are literal" in system
    assert "No markdown fences" in system


@pytest.mark.unit
async def test_build_d4_location_batch_tasks_use_typed_payload_and_preserve_tags():
    data = MagicMock()
    data.commit = AsyncMock()
    data.get_zone = AsyncMock(return_value=None)
    data.get_nodes_in_rect = AsyncMock()
    data.update_content = AsyncMock()
    data.update_flags = AsyncMock()

    target = MagicMock(
        x=45,
        y=52,
        zone_id="D4_0_1",
        terrain_type="city_gate_outer",
        content={"environment_tags": ["ancient_city", "city_ruins", "gate", "locked_exit"]},
        flags={
            "is_gate": True,
            "district_key": "D4_0_1",
            "district_profile": {
                "name": "Западный рынок обломков",
                "role": "scavenged stalls and side streets",
                "tags": ["broken_market"],
            },
        },
        movement_profile={
            "has_road": True,
            "route": {"type": "ancient_highway", "tags": ["road", "ancient_highway", "main_route"]},
        },
    )
    neighbor = MagicMock(
        x=46,
        y=52,
        zone_id="D4_0_1",
        content={"environment_tags": ["ancient_city", "ancient_highway"]},
        flags={},
        movement_profile={
            "has_road": True,
            "route": {"type": "ancient_highway", "tags": ["road", "ancient_highway", "main_route"]},
        },
    )
    data.get_nodes_in_rect.return_value = [target, neighbor]
    generator = LLMWorldGenerator(data, generation_ai=None)

    specs = await generator._build_d4_location_batch_task_specs()

    assert len(specs) == 1
    assert specs[0].task_type == "world.location_batch"
    payload = specs[0].input_payload["batch"]
    assert payload[0]["id"] == "45_52"
    assert "city_ruins_edge" in payload[0]["tags"]
    assert "road" in payload[0]["tags"]
    assert payload[0]["context"]
    assert payload[0]["district_context"]["name"] == "Западный рынок обломков"
    assert "route_context" in payload[0]
    assert "boundary_context" in payload[0]
    data.update_content.assert_not_awaited()
    data.update_flags.assert_not_awaited()


@pytest.mark.unit
async def test_run_full_mode_commits_seed_before_ai_enrichment():
    events = []
    data = MagicMock()
    data.commit = AsyncMock(side_effect=lambda: events.append("commit"))
    generation_ai = FakeGenerationAI()
    generator = LLMWorldGenerator(data, generation_ai=generation_ai)
    generator._generate_world_shell = AsyncMock()
    generator._generate_d4_capital = AsyncMock()
    generator.village_loader.load_village = AsyncMock()
    generator._enqueue_world_ai_tasks = AsyncMock(side_effect=lambda: events.append("enqueue_ai"))

    await generator.run("full")

    data.commit.assert_awaited_once()
    assert events == ["commit", "enqueue_ai"]
    generator._generate_world_shell.assert_awaited_once()
    generator._generate_d4_capital.assert_awaited_once()
    generator.village_loader.load_village.assert_awaited_once()
    generator._enqueue_world_ai_tasks.assert_awaited_once()


@pytest.mark.unit
async def test_run_full_ai_mode_commits_seed_before_ai_enrichment():
    events = []
    data = MagicMock()
    data.commit = AsyncMock(side_effect=lambda: events.append("commit"))
    generator = LLMWorldGenerator(data, generation_ai=FakeGenerationAI())
    generator._generate_world_shell = AsyncMock()
    generator._generate_d4_capital = AsyncMock()
    generator.village_loader.load_village = AsyncMock()
    generator._enqueue_world_ai_tasks = AsyncMock(side_effect=lambda: events.append("enqueue_ai"))

    await generator.run("full_ai")

    data.commit.assert_awaited_once()
    assert events == ["commit", "enqueue_ai"]
    generator._enqueue_world_ai_tasks.assert_awaited_once()


@pytest.mark.unit
async def test_build_d4_location_batch_tasks_batch_district_as_five_sublocations():
    data = MagicMock()
    data.commit = AsyncMock()
    data.get_zone = AsyncMock(return_value=None)
    data.get_nodes_in_rect = AsyncMock()
    data.update_content = AsyncMock()
    data.update_flags = AsyncMock()

    nodes = [
        MagicMock(
            x=x,
            y=y,
            zone_id="D4_0_0",
            terrain_type="city_ruins",
            content={"environment_tags": ["ancient_city", "city_ruins"]},
            flags={},
        )
        for x in range(45, 50)
        for y in range(45, 50)
    ]
    data.get_nodes_in_rect.return_value = nodes
    generator = LLMWorldGenerator(data, generation_ai=None)

    specs = await generator._build_d4_location_batch_task_specs()
    payloads = [spec.input_payload["batch"] for spec in specs]
    assert [len(payload) for payload in payloads] == [5, 5, 5, 5, 5]
    assert all(item["district_context"] is None for payload in payloads for item in payload)


@pytest.mark.unit
async def test_run_ai_mode_enqueues_world_ai_tasks_without_provider_calls():
    data = MagicMock()
    data.commit = AsyncMock()
    data.get_zone = AsyncMock(
        return_value=SimpleNamespace(
            id="D4_1_1",
            region_id="D4",
            biome_id="city_ruins",
            tier=0,
            flags={"narrative_context": "Former capital safe hub."},
        )
    )
    data.get_nodes_in_rect = AsyncMock(return_value=[
        MagicMock(
            x=45,
            y=45,
            zone_id="D4_0_0",
            terrain_type="outer_monolith_wall_walk",
            content={"environment_tags": ["ancient_city", "outer_monolith_wall"]},
            flags={},
        )
    ])
    generation_ai = FakeGenerationAI()
    generator = LLMWorldGenerator(data, generation_ai=generation_ai)

    await generator.run("ai")

    assert generation_ai.specs is not None
    assert {spec.task_type for spec in generation_ai.specs} == {"world.zone_lore", "world.location_batch"}
    data.update_content.assert_not_called()
    data.update_flags.assert_not_called()
