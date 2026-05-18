from __future__ import annotations

import time

from fastapi import Request

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap
from src.frontend.core.database.session import get_session_context
from src.frontend.features.player_analytics.repositories.daily_activity_repository import (
    PlayerDailyActivityRepository,
)

_ONLINE_WINDOW = 300  # 5 minutes — player is "online" if active within this window


async def _online_now_provider(request: Request) -> MetricWidgetMap:
    presence: dict[str, float] = getattr(request.app.state, "player_presence", {})
    cutoff = time.time() - _ONLINE_WINDOW
    online = sum(1 for ts in presence.values() if ts > cutoff)
    return MetricWidgetMap(
        key="online_now",
        title="Онлайн сейчас",
        value=str(online),
        subtitle="Активны за последние 5 мин",
    )


async def _dau_today_provider(request: Request) -> MetricWidgetMap:
    presence: dict[str, float] = getattr(request.app.state, "player_presence", {})
    unique_today = len(presence)
    try:
        async with get_session_context() as session:
            db_count = await PlayerDailyActivityRepository(session).get_today_dau()
        unique_today = max(unique_today, db_count)
    except Exception:
        pass
    return MetricWidgetMap(
        key="dau_today",
        title="Уникальных игроков сегодня",
        value=str(unique_today),
    )


async def _dau_history_provider(request: Request) -> TableWidgetMap:
    rows: list[dict[str, object]] = []
    try:
        async with get_session_context() as session:
            rows = await PlayerDailyActivityRepository(session).get_dau_history(days=30)
    except Exception:
        pass
    return TableWidgetMap(
        key="dau_history",
        title="DAU за последние 30 дней",
        columns=[
            TableColumnMap(key="date", label="Дата"),
            TableColumnMap(key="dau", label="Уникальных игроков", align="right"),
        ],
        rows=rows,
    )


class PlayerAnalyticsAdmin(CabinetAdmin):
    key = "player_analytics"
    label = "Онлайн игроков"
    group = "site"
    group_label = "Сайт"
    path = "/admin/player-analytics"
    order = 2
    sidebar = (
        SidebarItem(key="overview", label="Онлайн / DAU", path="/admin/player-analytics", order=10),
    )
    dashboard_widgets = (
        MetricWidget(key="online_now", title="Онлайн сейчас", provider="player.online_now", order=10),
        MetricWidget(key="dau_today", title="Игроков сегодня", provider="player.dau_today", order=20),
        TableWidget(key="dau_history", title="DAU история", provider="player.dau_history", order=30),
    )
    providers = {
        "player.online_now": _online_now_provider,
        "player.dau_today": _dau_today_provider,
        "player.dau_history": _dau_history_provider,
    }


cabinet_site.register(PlayerAnalyticsAdmin)
