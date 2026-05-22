import httpx
from fastapi import Request

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap
from src.frontend.config.settings import settings
from src.frontend.core.database.session import get_session_context
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.features.cabinet.modules.site_analytics.mapper import SiteAnalyticsCabinetMapper
from src.frontend.features.cabinet.modules.site_analytics.service import SiteAnalyticsCabinetService
from src.frontend.integrations.backend_api.combat_sessions import CombatSessionsApi
from src.frontend.integrations.backend_api.exploration_sessions import ExplorationSessionsApi
from src.frontend.integrations.backend_api.scenario_sessions import ScenarioSessionsApi


async def _visits_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().visits_metric(snapshot)


async def _registrations_provider(request: Request) -> MetricWidgetMap:
    value = "—"
    subtitle = "site.auth_users"
    try:
        async with get_session_context() as session:
            value = str(await UserRepository(session).count_all())
    except Exception:
        subtitle = "site DB недоступна"
    return MetricWidgetMap(
        key="registrations",
        title="Регистраций",
        value=value,
        subtitle=subtitle,
    )


async def _lobby_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().lobby_metric(snapshot)


async def _game_joins_provider(request: Request) -> MetricWidgetMap:
    snapshot = await SiteAnalyticsCabinetService().get_snapshot(request)
    return SiteAnalyticsCabinetMapper().game_joins_metric(snapshot)


async def _active_combats_provider(request: Request) -> MetricWidgetMap:
    return await _active_sessions_metric(
        request,
        api_cls=CombatSessionsApi,
        key="active_combats",
        title="Активных боёв",
    )


async def _active_scenarios_provider(request: Request) -> MetricWidgetMap:
    return await _active_sessions_metric(
        request,
        api_cls=ScenarioSessionsApi,
        key="active_scenarios",
        title="Активных сценариев",
    )


async def _active_travels_provider(request: Request) -> MetricWidgetMap:
    return await _active_sessions_metric(
        request,
        api_cls=ExplorationSessionsApi,
        key="active_travels",
        title="Активных путешествий",
    )


async def _active_sessions_metric(request: Request, *, api_cls, key: str, title: str) -> MetricWidgetMap:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = api_cls(client=client, base_url=settings.backend_base_url)
    subtitle = "game backend"
    try:
        value = str(len(await api.list_active()))
    except (httpx.HTTPStatusError, httpx.RequestError):
        value = "0"
        subtitle = "game backend недоступен"
    return MetricWidgetMap(key=key, title=title, value=value, subtitle=subtitle)


class SiteAnalyticsAdmin(CabinetAdmin):
    key = "site_analytics"
    label = "Аналитика сайта"
    group = "site"
    group_label = "Сайт"
    path = "/admin/site-analytics"
    order = 1
    sidebar = (SidebarItem(key="overview", label="Обзор", path="/admin/site-analytics", order=10),)
    dashboard_widgets = (
        MetricWidget(key="visits_total", title="Визиты (с запуска)", provider="site.visits", order=10),
        MetricWidget(key="registrations", title="Регистраций", provider="site.registrations", order=20),
        MetricWidget(key="lobby_visits", title="Входов в лобби", provider="site.lobby", order=30),
        MetricWidget(key="game_joins", title="Нажали «Войти в игру»", provider="site.game_joins", order=40),
        MetricWidget(key="active_combats", title="Активных боёв", provider="site.active_combats", order=50),
        MetricWidget(key="active_scenarios", title="Активных сценариев", provider="site.active_scenarios", order=60),
        MetricWidget(key="active_travels", title="Активных путешествий", provider="site.active_travels", order=70),
    )
    providers = {
        "site.visits": _visits_provider,
        "site.registrations": _registrations_provider,
        "site.lobby": _lobby_provider,
        "site.game_joins": _game_joins_provider,
        "site.active_combats": _active_combats_provider,
        "site.active_scenarios": _active_scenarios_provider,
        "site.active_travels": _active_travels_provider,
    }


cabinet_site.register(SiteAnalyticsAdmin)
