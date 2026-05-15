from fastapi import Request

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap
from src.frontend.features.cabinet.modules.game_server.mapper import GameServerCabinetMapper
from src.frontend.features.cabinet.modules.game_server.service import GameServerCabinetService


async def game_server_status_provider(request: Request) -> MetricWidgetMap:
    snapshot = await GameServerCabinetService().get_snapshot(request)
    return GameServerCabinetMapper().status_metric(snapshot)


async def game_server_checks_provider(request: Request) -> ListWidgetMap:
    snapshot = await GameServerCabinetService().get_snapshot(request)
    return GameServerCabinetMapper().checks_list(snapshot)


class GameServerAdmin(CabinetAdmin):
    key = "game_server"
    label = "Игровой сервер"
    group = "game_server"
    group_label = "Гейм Сервер"
    icon = "server"
    path = "/cabinet/game-server"
    sidebar = (SidebarItem(key="overview", label="Overview", path="/cabinet/game-server"),)
    dashboard_widgets = (
        MetricWidget(key="game_server_status", title="Game Server Status", provider="game_server.status", order=10),
        ListWidget(key="game_server_checks", title="Runtime Checks", provider="game_server.checks", order=20),
    )
    providers = {
        "game_server.status": game_server_status_provider,
        "game_server.checks": game_server_checks_provider,
    }


cabinet_site.register(GameServerAdmin)
