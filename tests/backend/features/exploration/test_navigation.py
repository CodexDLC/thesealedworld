# tests/backend/features/exploration/test_navigation.py
from pathlib import Path

import pytest

from src.backend.features.exploration.gateway.exploration_gateway import ExplorationGateway
from src.backend.features.exploration.runtime.city_map import build_city_map_payload
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.backend.features.exploration.services.navigation_service import ExplorationNavigationService
from src.backend.features.world.resources.static.d4_city_map import build_d4_city_map_node_metadata
from src.shared.schemas.exploration import MoveRequest, NavigationActionsDTO, NavigationGridDTO

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_navigation_grid_generation():
    current_loc = "50_50"
    exits = {
        "nav:50_49": {"time_duration": 1.0},  # North
        "nav:50_51": {"time_duration": 1.0},  # South
        "nav:49_50": {"time_duration": 1.0},  # West
        "nav:51_50": {"time_duration": 1.0},  # East
        "svc:shop": {"text_button": "Store"},
    }
    flags = {"is_safe_zone": True, "threat_tier": 0}

    grid = NavigationEngine.build_grid(current_loc, exits, flags)

    assert isinstance(grid, NavigationGridDTO)
    # Check directions
    assert grid.n.is_active is True
    assert "move:50_49" in grid.n.action
    assert grid.s.is_active is True
    assert "move:50_51" in grid.s.action

    # Check center
    assert grid.center.id == "look"

    # Check services
    assert len(grid.services) == 1
    assert grid.services[0].label == "🚪 Store"


def test_navigation_grid_with_walls():
    current_loc = "50_50"
    exits = {
        "nav:50_49": {"time_duration": 1.0},  # North only
    }
    flags = {}

    grid = NavigationEngine.build_grid(current_loc, exits, flags)

    assert grid.n.is_active is True
    assert grid.s.is_active is False
    assert grid.s.label == "⛔️"


def test_navigation_actions_group_web_contract():
    current_loc = "50_50"
    exits = {
        "nav:50_49": {"time_duration": 1.0, "desc_next_room": "Северные ворота"},
        "nav:51_50": {"time_duration": 1.0},
        "svc:arena": {"text_button": "Arena"},
    }
    flags = {"is_safe_zone": False, "threat_tier": 0.35}

    actions = NavigationEngine.build_actions(current_loc, exits, flags)

    assert isinstance(actions, NavigationActionsDTO)
    assert actions.movement["north"].action == "move:50_49:1.0"
    assert actions.movement["north"].tooltip == "Перейти: Северные ворота"
    assert actions.movement["east"].action == "move:51_50:1.0"
    assert actions.movement["south"].is_active is False
    assert actions.exploration["explore"].action == "interact:search"
    assert actions.services["svc_arena"].action == "service:arena"
    assert actions.auto_routes["home"].is_active is False
    assert actions.context["threat_tier"] == 0.35


def test_navigation_city_shield_does_not_make_unsafe_ruins_safe():
    actions = NavigationEngine.build_actions(
        "50_50",
        {},
        {"is_safe_zone": False, "threat_tier": 1},
        {"is_inside_city_shield": True},
    )

    assert actions.context["is_safe_zone"] is False
    assert actions.movement["north"].is_active is False


def test_navigation_threat_tier_zero_is_not_safe_without_system_connect():
    actions = NavigationEngine.build_actions("50_50", {}, {"is_safe_zone": False, "threat_tier": 0})

    assert actions.context["is_safe_zone"] is False
    assert actions.context["system_connect"] is False


def test_navigation_system_connect_marks_safe_context():
    actions = NavigationEngine.build_actions("52_52", {}, {"system_connect": True, "threat_tier": 2})

    assert actions.context["is_safe_zone"] is True
    assert actions.context["system_connect"] is True


def test_service_action_uses_backend_opaque_service_id():
    actions = NavigationEngine.build_actions("52_51", {"svc:svc_arena_main": {"text_button": "Arena"}}, {})

    service = actions.services["svc_svc_arena_main"]

    assert service.action == "service:svc_arena_main"


def test_move_request_accepts_target_location_id_without_direction():
    request = MoveRequest(char_id=1, target_id="52_51")

    assert request.char_id == 1
    assert request.target_id == "52_51"
    assert request.direction is None


class FakeLocalMapIntegrator:
    def __init__(self) -> None:
        self.locations = {
            "52_52": {
                "loc_id": "52_52",
                "name": "Площадь Исхода",
                "description": "Центральная площадь.",
                "background_url": "/static/images/exploration/city/d4/52_52_runic_circle_plaza.png",
                "exits": {
                    "nav:52_51": {"desc_next_room": "Северный проспект", "time_duration": 2.0},
                    "nav:53_52": {"desc_next_room": "Восточный тракт", "time_duration": 2.0},
                    "svc:svc_portal_hub": {"text_button": "К Порталу"},
                },
                "flags": {
                    "is_safe_zone": True,
                    "system_connect": True,
                    "threat_tier": 0,
                    "city_map": build_d4_city_map_node_metadata(52, 52),
                },
                "anchor_influence": {"threat": 0.0, "dominant_anchor": "portal", "tags": ["safe_zone"]},
                "movement_profile": {"blocked_exits": ["west"], "gated_exits": {"south": {"state": "locked"}}},
                "services": ["svc_portal_hub"],
                "tags": ["hub_center", "safe_zone"],
                "terrain": "ancient_pavement",
                "node_type": "hub",
                "zone_id": "D4_1_1",
                "world_zone": {"id": "D4_1_1", "tier": 0},
            },
            "52_51": {
                "loc_id": "52_51",
                "name": "Северный проспект",
                "description": "Улица к башне.",
                "exits": {"nav:52_52": {"desc_next_room": "Площадь Исхода", "time_duration": 2.0}},
                "flags": {"is_safe_zone": True, "threat_tier": 0},
                "anchor_influence": {"threat": 0.1},
                "movement_profile": {"blocked_exits": []},
                "services": ["svc_arena_main"],
            },
            "53_52": {
                "loc_id": "53_52",
                "name": "Восточный тракт",
                "description": "Широкая улица к воротам.",
                "exits": {"nav:52_52": {"desc_next_room": "Площадь Исхода", "time_duration": 2.0}},
                "flags": {"is_safe_zone": True, "threat_tier": 0},
                "anchor_influence": {"threat": 0.05},
                "movement_profile": {"blocked_exits": []},
                "services": [],
            },
        }

    async def get_player_location_id(self, char_id: int) -> str:
        return "52_52"

    async def get_location_data(self, loc_id: str) -> dict:
        return self.locations.get(loc_id, {})

    async def get_players_count(self, loc_id: str, exclude_char_id: int | None = None) -> int:
        return {"52_52": 1, "52_51": 2}.get(loc_id, 0)

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        return {"battle-1": "Training"} if loc_id == "53_52" else {}

    async def get_corpse_count(self, loc_id: str) -> int | None:
        return 3 if loc_id == "52_51" else 0

    async def set_world_theme(self, char_id: int, world_theme: dict) -> None:
        pass


@pytest.mark.asyncio
async def test_local_map_builds_area_from_runtime_location_cache() -> None:
    service = ExplorationNavigationService(FakeLocalMapIntegrator())  # type: ignore[arg-type]

    result = await service.build_local_map(char_id=7, radius=1)

    assert result.char_id == 7
    assert result.current_loc_id == "52_52"
    assert result.radius == 1
    assert result.size == 3
    assert len(result.rows) == 3
    assert len(result.rows[0]) == 3

    current = result.rows[1][1]
    assert current.is_current is True
    assert current.loc_id == "52_52"
    assert current.title == "Площадь Исхода"
    assert current.description == "Центральная площадь."
    assert current.background_available is True
    assert current.service_count == 1
    assert current.service_labels == ["К порталу"]
    assert current.players_count == 1
    assert current.battles_count == 0
    assert current.corpse_count == 0
    assert current.tooltip["title"] == "Площадь Исхода"
    assert current.tooltip["services_count"] == 1
    assert current.tooltip["service_labels"] == ["К порталу"]

    assert current.edges["north"].state == "open"
    assert current.edges["north"].target_loc_id == "52_51"
    assert current.edges["north"].label == "Северный проспект"
    assert current.edges["east"].state == "open"
    assert current.edges["west"].state == "blocked"
    assert current.edges["south"].state == "locked"
    assert "west" not in current.render_edges
    assert "south" not in current.render_edges

    west_unknown = result.rows[1][0]
    assert west_unknown.loc_id == "51_52"
    assert west_unknown.render_edges["east"].state == "blocked"

    south_unknown = result.rows[2][1]
    assert south_unknown.loc_id == "52_53"
    assert south_unknown.render_edges["north"].state == "locked"

    north = result.rows[0][1]
    assert north.loc_id == "52_51"
    assert north.is_known is True
    assert north.service_count == 1
    assert north.service_labels == ["На арену"]
    assert north.players_count == 2
    assert north.corpse_count == 3

    east = result.rows[1][2]
    assert east.loc_id == "53_52"
    assert east.battles_count == 1

    unknown = result.rows[0][0]
    assert unknown.loc_id == "51_51"
    assert unknown.is_known is False
    assert unknown.title is None
    assert unknown.edges["north"].state == "unknown"


@pytest.mark.asyncio
async def test_navigation_builds_city_map_district_payload_from_runtime_flags() -> None:
    service = ExplorationNavigationService(FakeLocalMapIntegrator())  # type: ignore[arg-type]

    result = await service.build_current_navigation(char_id=7)

    assert result.background_url is None
    assert result.city_map["mode"] == "viewport_7x7"
    assert result.city_map["size"] == 7
    assert result.city_map["district"]["key"] == "D4_CITY_1_1"
    assert result.city_map["current"] == {"visual_x": 8, "visual_y": 8, "local_x": 2, "local_y": 2}
    assert result.city_map["viewport"] == {"visual_x": 5, "visual_y": 5, "max_visual_x": 11, "max_visual_y": 11}
    assert len(result.city_map["rows"]) == 7
    assert len(result.city_map["rows"][0]) == 7
    assert result.city_map["rows"][0][0]["tile_url"].endswith("/d4_05_05.webp")
    assert result.city_map["rows"][3][3]["is_current"] is True
    assert "service_marker" not in result.city_map["rows"][2][2]
    assert result.city_map["rows"][2][2]["service_markers"] == [
        {
            "service_id": "svc_arena_main",
            "service_type": "arena",
            "label": "Арена",
            "icon_url": "/static/images/ui/service-icons/arena.svg",
            "corner": "top-left",
        }
    ]
    assert result.city_map["rows"][2][4]["service_markers"][0]["label"] == "Торговый зал"
    assert result.city_map["rows"][2][4]["service_markers"][0]["corner"] == "top-left"
    assert result.city_map["rows"][4][2]["service_markers"][0]["label"] == "Реестр"
    assert result.city_map["rows"][4][2]["service_markers"][0]["corner"] == "top-left"
    assert result.city_map["rows"][4][4]["service_markers"][0]["label"] == "Постоялый двор"
    assert result.city_map["rows"][4][4]["service_markers"][0]["corner"] == "top-right"
    assert result.city_map["rows"][5][1]["service_markers"][0]["label"] == "Ремесленный двор"
    assert result.city_map["rows"][5][1]["service_markers"][0]["corner"] == "top-right"
    assert result.city_map["rows"][6][6]["tile_url"].endswith("/d4_11_11.webp")


@pytest.mark.asyncio
async def test_exploration_screen_context_keeps_city_map_and_drops_legacy_d4_background() -> None:
    service = ExplorationNavigationService(FakeLocalMapIntegrator())  # type: ignore[arg-type]

    navigation = await service.build_current_navigation(char_id=7)
    context = ExplorationGateway._screen_context(navigation)

    assert context.background_url is None
    assert context.city_map == navigation.city_map
    assert context.city_map["rows"][3][3]["is_current"] is True


def test_navigation_service_has_no_generated_terrain_background_fallback() -> None:
    source = (PROJECT_ROOT / "src/backend/features/exploration/services/navigation_service.py").read_text(
        encoding="utf-8"
    )

    assert "terrain_fallback" not in source
    assert "biome_fallback" not in source
    assert "city_ruins_collapsed_district_01.webp" not in source


def test_city_map_viewport_clamps_to_visual_contour_near_city_edge() -> None:
    result = build_city_map_payload("45_45", {"flags": {"city_map": build_d4_city_map_node_metadata(45, 45)}})

    assert result["mode"] == "viewport_7x7"
    assert result["viewport"] == {"visual_x": 0, "visual_y": 0, "max_visual_x": 6, "max_visual_y": 6}
    assert result["rows"][0][0]["tile_url"].endswith("/d4_00_00.webp")
    assert result["rows"][1][1]["is_current"] is True
    assert result["rows"][6][6]["tile_url"].endswith("/d4_06_06.webp")
