from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.exploration_sessions import ExplorationSessionsApi

if TYPE_CHECKING:
    from fastapi import Request


async def _active_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="active_travels", title="Активных путешествий", value="—")


async def _encounters_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="total_encounters", title="Энкаунтеров всего", value="—")


async def _events_provider(request: Request) -> MetricWidgetMap:
    return MetricWidgetMap(key="events_fired", title="Событий сработало", value="—")


async def _recent_provider(request: Request) -> TableWidgetMap:
    return TableWidgetMap(
        key="recent_travels",
        title="Последние путешествия",
        columns=[
            TableColumnMap(key="id", label="ID"),
            TableColumnMap(key="player", label="Игрок"),
            TableColumnMap(key="location", label="Локация"),
            TableColumnMap(key="status", label="Статус"),
            TableColumnMap(key="date", label="Дата"),
        ],
        rows=[],
    )


async def _sessions_provider(request: Request) -> TableWidgetMap:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = ExplorationSessionsApi(client=client, base_url=settings.backend_base_url)
    try:
        sessions = await api.list_active()
    except (httpx.HTTPStatusError, httpx.RequestError):
        sessions = []
    return TableWidgetMap(
        key="exploration_sessions",
        title="Активные путешествия",
        columns=[
            TableColumnMap(key="encounter_id", label="Энкаунтер"),
            TableColumnMap(key="char_id", label="Персонаж"),
            TableColumnMap(key="type", label="Тип"),
            TableColumnMap(key="title", label="Название"),
            TableColumnMap(key="status", label="Статус"),
        ],
        rows=sessions,
    )


async def _analytics_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="exploration_analytics",
        title="Аналитика",
        items=["Графики и метрики путешествий — будет добавлено в следующей итерации"],
    )


class ExplorationAdmin(CabinetAdmin):
    key = "exploration"
    label = "Путешествия"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/admin/exploration"
    order = 70
    sidebar = (
        SidebarItem(key="dashboard", label="Дашборд", path="/admin/exploration", order=10),
        SidebarItem(key="sessions", label="Активные путешествия", path="/admin/exploration/sessions", order=20),
        SidebarItem(key="analytics", label="Аналитика", path="/admin/exploration/analytics", order=30),
    )
    dashboard_widgets = (
        MetricWidget(key="active_travels", title="Активных путешествий", provider="exploration.active", order=10),
        MetricWidget(key="total_encounters", title="Энкаунтеров всего", provider="exploration.encounters", order=20),
        MetricWidget(key="events_fired", title="Событий сработало", provider="exploration.events", order=30),
        TableWidget(key="recent_travels", title="Последние путешествия", provider="exploration.recent", order=40),
    )
    sub_pages = {
        "sessions": (
            TableWidget(
                key="exploration_sessions", title="Активные путешествия", provider="exploration.sessions", order=10
            ),
        ),
        "analytics": (
            ListWidget(key="exploration_analytics", title="Аналитика", provider="exploration.analytics", order=10),
        ),
    }
    providers = {
        "exploration.active": _active_provider,
        "exploration.encounters": _encounters_provider,
        "exploration.events": _events_provider,
        "exploration.recent": _recent_provider,
        "exploration.sessions": _sessions_provider,
        "exploration.analytics": _analytics_provider,
    }


cabinet_site.register(ExplorationAdmin)
