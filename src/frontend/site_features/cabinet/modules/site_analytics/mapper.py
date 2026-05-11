from fastapi_cabinet.contracts.widgets import MetricWidgetMap
from src.frontend.site_features.cabinet.modules.site_analytics.service import SiteAnalyticsSnapshot


class SiteAnalyticsCabinetMapper:
    def visits_metric(self, snapshot: SiteAnalyticsSnapshot) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="visits_total",
            title="Визиты (с запуска)",
            value=str(snapshot.visits),
            subtitle="Сбрасывается при перезапуске сервера",
        )

    def registrations_metric(self, snapshot: SiteAnalyticsSnapshot) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="registrations",
            title="Регистраций",
            value=str(snapshot.registrations),
        )

    def lobby_metric(self, snapshot: SiteAnalyticsSnapshot) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="lobby_visits",
            title="Входов в лобби",
            value=str(snapshot.lobby_visits),
        )

    def game_joins_metric(self, snapshot: SiteAnalyticsSnapshot) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="game_joins",
            title="Нажали «Войти в игру»",
            value=str(snapshot.game_joins),
        )
