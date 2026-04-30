import pytest
from unittest.mock import MagicMock
from src.backend.features.world.services.navigation_service import WorldNavigationService

@pytest.mark.unit
class TestWorldNavigationService:
    def test_calculate_exits_simple(self):
        service = WorldNavigationService()

        node = MagicMock()
        node.x, node.y = 52, 52
        node.flags = {"has_road": True}
        node.services = ["portal"]
        node.zone_id = "region1_zone1"

        neighbor = MagicMock()
        neighbor.x, neighbor.y = 52, 51 # North
        neighbor.is_active = True
        neighbor.flags = {"has_road": True}
        neighbor.zone_id = "region1_zone2"
        neighbor.content = {"title": "Neighbor Node"}

        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)

        assert "svc:portal" in exits
        assert exits["svc:portal"]["text_button"] == "К Порталу"

        assert "nav:52_51" in exits
        assert exits["nav:52_51"]["desc_next_room"] == "Neighbor Node"
        assert exits["nav:52_51"]["time_duration"] == 2.0 # Both have roads

    def test_calculate_exits_restricted(self):
        service = WorldNavigationService()
        node = MagicMock(x=52, y=52, flags={"restricted_exits": ["north"]}, services=None, zone_id="z1")
        neighbor = MagicMock(x=52, y=51, is_active=True, zone_id="z1")
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_calculate_exits_cross_region_no_road(self):
        service = WorldNavigationService()
        node = MagicMock(x=52, y=52, flags={"has_road": False}, services=None, zone_id="r1_z1")
        neighbor = MagicMock(x=52, y=51, is_active=True, flags={"has_road": False}, zone_id="r2_z1")
        node_map = {"52_51": neighbor}

        exits = service.calculate_exits(node, node_map)
        assert "nav:52_51" not in exits

    def test_service_labels(self):
        service = WorldNavigationService()
        assert service._service_labels("tavern") == ("В Таверну", "Войти в Таверну")
        assert service._service_labels("arena") == ("На Арену", "Выйти на Арену")
        assert service._service_labels("unknown") == ("Войти", "Вход в Сервис")
