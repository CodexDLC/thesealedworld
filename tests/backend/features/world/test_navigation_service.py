from unittest.mock import MagicMock

import pytest

from src.backend.features.world.services.navigation_service import WorldNavigationService


def _movement(
    *,
    blocked_exits: list[str] | None = None,
    gated_exits: dict | None = None,
    has_road: bool = False,
    travel_cost: float = 1.0,
    is_passable: bool = True,
) -> dict:
    return {
        "blocked_exits": blocked_exits or [],
        "gated_exits": gated_exits or {},
        "has_road": has_road,
        "travel_cost": travel_cost,
        "is_passable": is_passable,
    }


@pytest.mark.unit
class TestWorldNavigationService:
    def test_calculate_exits_simple(self):
        service = WorldNavigationService()

        node = MagicMock()
        node.x, node.y = 52, 52
        node.flags = {}
        node.movement_profile = _movement(has_road=True)
        node.services = ["portal"]
        node.zone_id = "region1_zone1"

        neighbor = MagicMock()
        neighbor.x, neighbor.y = 52, 51 # North
        neighbor.is_active = True
        neighbor.flags = {}
        neighbor.movement_profile = _movement(has_road=True)
        neighbor.zone_id = "region1_zone2"
        neighbor.content = {"title": "Neighbor Node"}

        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)

        assert "svc:portal" in exits
        assert exits["svc:portal"]["text_button"] == "К Порталу"

        assert "nav:52_51" in exits
        assert exits["nav:52_51"]["desc_next_room"] == "Neighbor Node"
        assert exits["nav:52_51"]["time_duration"] == 2.0  # Both have roads

    def test_calculate_exits_blocked_direction(self):
        service = WorldNavigationService()
        node = MagicMock(
            x=52,
            y=52,
            flags={},
            movement_profile=_movement(blocked_exits=["north"]),
            services=None,
            zone_id="z1",
        )
        neighbor = MagicMock(x=52, y=51, is_active=True, flags={}, movement_profile=_movement(), zone_id="z1")
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_calculate_exits_respects_neighbor_reverse_block(self):
        service = WorldNavigationService()
        node = MagicMock(x=52, y=52, flags={}, movement_profile=_movement(), services=None, zone_id="z1")
        neighbor = MagicMock(
            x=52,
            y=51,
            is_active=True,
            flags={},
            movement_profile=_movement(blocked_exits=["south"]),
            zone_id="z1",
        )
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_calculate_exits_skips_locked_gate(self):
        service = WorldNavigationService()
        node = MagicMock(
            x=52,
            y=52,
            flags={},
            movement_profile=_movement(gated_exits={"north": {"state": "locked"}}),
            services=None,
            zone_id="z1",
        )
        neighbor = MagicMock(x=52, y=51, is_active=True, flags={}, movement_profile=_movement(), zone_id="z1")
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_calculate_exits_skips_not_passable_neighbor(self):
        service = WorldNavigationService()
        node = MagicMock(x=52, y=52, flags={}, movement_profile=_movement(), services=None, zone_id="z1")
        neighbor = MagicMock(
            x=52,
            y=51,
            is_active=True,
            flags={},
            movement_profile=_movement(is_passable=False),
            zone_id="z1",
        )
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_calculate_exits_uses_travel_cost_off_road(self):
        service = WorldNavigationService()
        node = MagicMock(x=52, y=52, flags={}, movement_profile=_movement(travel_cost=1.25), services=None, zone_id="z1")
        neighbor = MagicMock(
            x=52,
            y=51,
            is_active=True,
            flags={},
            movement_profile=_movement(travel_cost=1.5),
            zone_id="z1",
            content={"title": "Slow ruins"},
        )
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert exits["nav:52_51"]["time_duration"] == 6.0

    def test_calculate_exits_cross_region_no_road(self):
        service = WorldNavigationService()
        node = MagicMock(x=52, y=52, flags={}, movement_profile=_movement(has_road=False), services=None, zone_id="r1_z1")
        neighbor = MagicMock(
            x=52,
            y=51,
            is_active=True,
            flags={},
            movement_profile=_movement(has_road=False),
            zone_id="r2_z1",
        )
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_service_labels(self):
        service = WorldNavigationService()
        assert service._service_labels("tavern") == ("В Постоялый Двор", "Войти в Постоялый Двор")
        assert service._service_labels("arena") == ("На Арену", "Выйти на Арену")
        assert service._service_labels("unknown") == ("Войти", "Вход в Сервис")
