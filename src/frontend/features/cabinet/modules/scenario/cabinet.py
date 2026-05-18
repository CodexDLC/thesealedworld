from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.scenario_sessions import ScenarioSessionsApi

if TYPE_CHECKING:
    from fastapi import Request


async def _active_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="active_scenarios", title="Активных сценариев", value="—")


async def _total_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="total_scenarios", title="Всего сценариев", value="—")


async def _completed_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="completed", title="Завершённых", value="—")


async def _recent_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="recent",
        title="Последние сценарии",
        columns=[
            TableColumnMap(key="id", label="ID"),
            TableColumnMap(key="type", label="Тип"),
            TableColumnMap(key="status", label="Статус"),
            TableColumnMap(key="player", label="Игрок"),
            TableColumnMap(key="date", label="Дата"),
        ],
        rows=[],
    )


async def _sessions_provider(request: Request) -> TableWidgetMap:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = ScenarioSessionsApi(client=client, base_url=settings.backend_base_url)
    try:
        sessions = await api.list_active()
    except (httpx.HTTPStatusError, httpx.RequestError):
        sessions = []
    return TableWidgetMap(
        key="scenario_sessions",
        title="Активные сценарии",
        columns=[
            TableColumnMap(key="char_id", label="Персонаж"),
            TableColumnMap(key="session_id", label="Сессия"),
            TableColumnMap(key="quest_key", label="Квест"),
            TableColumnMap(key="current_node", label="Узел"),
            TableColumnMap(key="step", label="Прогресс"),
            TableColumnMap(key="updated_at", label="Обновлено"),
        ],
        rows=sessions,
    )


async def _analytics_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="scenario_analytics",
        title="Аналитика",
        items=["Графики и метрики сценариев — будет добавлено в следующей итерации"],
    )


class ScenarioAdmin(CabinetAdmin):
    key = "scenario"
    label = "Сценарии"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/admin/scenario"
    order = 60
    sidebar = (
        SidebarItem(key="dashboard", label="Дашборд", path="/admin/scenario", order=10),
        SidebarItem(key="sessions", label="Активные сценарии", path="/admin/scenario/sessions", order=20),
        SidebarItem(key="analytics", label="Аналитика", path="/admin/scenario/analytics", order=30),
    )
    dashboard_widgets = (
        MetricWidget(key="active_scenarios", title="Активных сценариев", provider="scenario.active", order=10),
        MetricWidget(key="total_scenarios", title="Всего сценариев", provider="scenario.total", order=20),
        MetricWidget(key="completed", title="Завершённых", provider="scenario.completed", order=30),
        TableWidget(key="recent", title="Последние сценарии", provider="scenario.recent", order=40),
    )
    sub_pages = {
        "sessions": (
            TableWidget(key="scenario_sessions", title="Активные сценарии", provider="scenario.sessions", order=10),
        ),
        "analytics": (
            ListWidget(key="scenario_analytics", title="Аналитика", provider="scenario.analytics", order=10),
        ),
    }
    providers = {
        "scenario.active": _active_provider,
        "scenario.total": _total_provider,
        "scenario.completed": _completed_provider,
        "scenario.recent": _recent_provider,
        "scenario.sessions": _sessions_provider,
        "scenario.analytics": _analytics_provider,
    }


cabinet_site.register(ScenarioAdmin)
