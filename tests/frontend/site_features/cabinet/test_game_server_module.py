from types import SimpleNamespace

from fastapi import Request

from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap
from src.frontend.site_features.cabinet.modules.game_server.cabinet import (
    GameServerAdmin,
    game_server_checks_provider,
    game_server_status_provider,
)
from src.frontend.site_features.cabinet.modules.game_server.mapper import GameServerCabinetMapper
from src.frontend.site_features.cabinet.modules.game_server.service import GameServerSnapshot


def test_game_server_mapper_builds_metric_and_list_maps() -> None:
    mapper = GameServerCabinetMapper()
    snapshot = GameServerSnapshot(service_name="Frontend", status="online", checks=("frontend_app",))

    metric = mapper.status_metric(snapshot)
    checks = mapper.checks_list(snapshot)

    assert metric == MetricWidgetMap(
        key="game_server_status",
        title="Game Server Status",
        value="online",
        subtitle="Frontend",
        icon="server",
    )
    assert checks == ListWidgetMap(key="game_server_checks", title="Runtime Checks", items=["frontend_app"])


async def test_game_server_providers_return_widget_maps() -> None:
    request = Request(
        {
            "type": "http",
            "app": SimpleNamespace(title="TurnBasedMMORPG Frontend"),
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
        }
    )

    metric = await game_server_status_provider(request)
    checks = await game_server_checks_provider(request)

    assert isinstance(metric, MetricWidgetMap)
    assert metric.value == "online"
    assert isinstance(checks, ListWidgetMap)
    assert "cabinet_engine" in checks.items


def test_game_server_admin_declares_widgets() -> None:
    assert [widget.key for widget in GameServerAdmin.dashboard_widgets] == [
        "game_server_status",
        "game_server_checks",
    ]
