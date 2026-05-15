from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap
from src.frontend.features.cabinet.modules.game_server.service import GameServerSnapshot


class GameServerCabinetMapper:
    def status_metric(self, snapshot: GameServerSnapshot) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="game_server_status",
            title="Game Server Status",
            value=snapshot.status,
            subtitle=snapshot.service_name,
            icon="server",
        )

    def checks_list(self, snapshot: GameServerSnapshot) -> ListWidgetMap:
        return ListWidgetMap(
            key="game_server_checks",
            title="Runtime Checks",
            items=list(snapshot.checks),
        )
