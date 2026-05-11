from fastapi import Request

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap
from src.frontend.site_features.cabinet.modules.site_analytics.mapper import SiteAnalyticsCabinetMapper
from src.frontend.site_features.cabinet.modules.site_analytics.service import SiteAnalyticsCabinetService


async def _visits_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().visits_metric(snapshot)


async def _registrations_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().registrations_metric(snapshot)


async def _lobby_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().lobby_metric(snapshot)


async def _game_joins_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().game_joins_metric(snapshot)


class SiteAnalyticsAdmin(CabinetAdmin):
    key = "site_analytics"
    label = "Аналитика сайта"
    group = "site"
    group_label = "Сайт"
    path = "/cabinet/site-analytics"
    order = 10
    sidebar = (SidebarItem(key="overview", label="Обзор", path="/cabinet/site-analytics", order=10),)
    dashboard_widgets = (
        MetricWidget(key="visits_total", title="Визиты (с запуска)", provider="site.visits", order=10),
        MetricWidget(key="registrations", title="Регистраций", provider="site.registrations", order=20),
        MetricWidget(key="lobby_visits", title="Входов в лобби", provider="site.lobby", order=30),
        MetricWidget(key="game_joins", title="Нажали «Войти в игру»", provider="site.game_joins", order=40),
    )
    providers = {
        "site.visits": _visits_provider,
        "site.registrations": _registrations_provider,
        "site.lobby": _lobby_provider,
        "site.game_joins": _game_joins_provider,
    }


cabinet_site.register(SiteAnalyticsAdmin)
