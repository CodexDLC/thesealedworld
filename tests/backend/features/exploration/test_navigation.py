# tests/backend/features/exploration/test_navigation.py
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.shared.schemas.exploration import MoveRequest, NavigationActionsDTO, NavigationGridDTO


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
        "nav:50_49": {"time_duration": 1.0},
        "nav:51_50": {"time_duration": 1.0},
        "svc:arena": {"text_button": "Arena"},
    }
    flags = {"is_safe_zone": False, "threat_tier": 0.35}

    actions = NavigationEngine.build_actions(current_loc, exits, flags)

    assert isinstance(actions, NavigationActionsDTO)
    assert actions.movement["north"].action == "move:50_49:1.0"
    assert actions.movement["east"].action == "move:51_50:1.0"
    assert actions.movement["south"].is_active is False
    assert actions.exploration["explore"].action == "interact:search"
    assert actions.services["svc_arena"].action == "service:arena"
    assert actions.auto_routes["home"].is_active is False
    assert actions.context["threat_tier"] == 0.35


def test_navigation_safe_context_accepts_top_level_anchor_influence():
    actions = NavigationEngine.build_actions(
        "50_50",
        {},
        {"is_safe_zone": False, "threat_tier": 1},
        {"is_inside_city_shield": True},
    )

    assert actions.context["is_safe_zone"] is True
    assert actions.movement["north"].is_active is False


def test_service_action_uses_backend_opaque_service_id():
    actions = NavigationEngine.build_actions("52_51", {"svc:svc_arena_main": {"text_button": "Arena"}}, {})

    service = actions.services["svc_svc_arena_main"]

    assert service.action == "service:svc_arena_main"


def test_move_request_accepts_target_location_id_without_direction():
    request = MoveRequest(char_id=1, target_id="52_51")

    assert request.char_id == 1
    assert request.target_id == "52_51"
    assert request.direction is None
