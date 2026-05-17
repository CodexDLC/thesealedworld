from __future__ import annotations

import httpx
from fastapi import Request
from starlette.responses import Response

from fastapi_cabinet import CabinetAdmin, ListWidget, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import ListWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.rendering.widget_mapper import resolve_admin_widgets
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.config.settings import settings
from src.frontend.features.cabinet.modules.combat.mapper import CombatCabinetMapper
from src.frontend.features.cabinet.modules.combat.service import CombatCabinetService
from src.frontend.integrations.backend_api.combat_sessions import CombatSessionsApi

_MOUNT_PATH = "/admin"
_DETAIL_URL = "/admin/combat/session-detail"


async def _active_provider(request: Request) -> MetricWidgetMap:
    stats = await CombatCabinetService().get_stats(request)
    return CombatCabinetMapper().active_metric(stats)


async def _completed_provider(request: Request) -> MetricWidgetMap:
    stats = await CombatCabinetService().get_stats(request)
    return CombatCabinetMapper().completed_metric(stats)


async def _total_provider(request: Request) -> MetricWidgetMap:
    stats = await CombatCabinetService().get_stats(request)
    return CombatCabinetMapper().total_metric(stats)


async def _recent_provider(request: Request) -> TableWidgetMap:
    stats = await CombatCabinetService().get_stats(request)
    return CombatCabinetMapper().recent_table(stats)


async def _sessions_provider(request: Request) -> TableWidgetMap:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = CombatSessionsApi(client=client, base_url=settings.backend_base_url)
    try:
        sessions = await api.list_active()
    except (httpx.HTTPStatusError, httpx.RequestError):
        sessions = []
    rows = [{**s, "href": f"{_DETAIL_URL}?id={s['session_id']}"} for s in sessions]
    return TableWidgetMap(
        key="combat_sessions",
        title="Активные бои",
        columns=[
            TableColumnMap(key="session_id", label="ID сессии"),
            TableColumnMap(key="status", label="Статус"),
            TableColumnMap(key="battle_type", label="Тип"),
            TableColumnMap(key="step", label="Раунд"),
            TableColumnMap(key="alive", label="Живых"),
            TableColumnMap(key="started_at", label="Начало"),
            TableColumnMap(key="idle", label="Idle"),
        ],
        rows=rows,
        row_href_key="href",
    )


async def _analytics_provider(request: Request) -> ListWidgetMap:
    return ListWidgetMap(
        key="combat_analytics",
        title="Аналитика",
        items=["Графики и метрики боёв — будет добавлено в следующей итерации"],
    )


# ── session-detail providers (read session_id from query params) ──────────


async def _detail_status_provider(request: Request) -> MetricWidgetMap:
    meta = await _fetch_session_meta(request)
    return MetricWidgetMap(
        key="detail_status",
        title="Статус",
        value=str(meta.get("status", "—")),
        subtitle="active=1" if str(meta.get("active", "0")) == "1" else "завершён",
    )


async def _detail_round_provider(request: Request) -> MetricWidgetMap:
    meta = await _fetch_session_meta(request)
    return MetricWidgetMap(key="detail_round", title="Раунд", value=str(meta.get("step_counter", "—")))


async def _detail_alive_provider(request: Request) -> MetricWidgetMap:
    meta = await _fetch_session_meta(request)
    return MetricWidgetMap(
        key="detail_alive", title="Живых участников", value=str(meta.get("active_actors_count", "—"))
    )


async def _detail_type_provider(request: Request) -> MetricWidgetMap:
    meta = await _fetch_session_meta(request)
    return MetricWidgetMap(key="detail_type", title="Тип боя", value=str(meta.get("battle_type", "—")))


async def _detail_meta_provider(request: Request) -> TableWidgetMap:
    meta = await _fetch_session_meta(request)
    skip = {"session_id", "active", "teams", "actors_info", "dead_actors", "alive_counts"}
    rows = [{"param": k, "value": str(v)} for k, v in meta.items() if k not in skip]
    return TableWidgetMap(
        key="detail_meta",
        title="Метаданные сессии",
        columns=[TableColumnMap(key="param", label="Параметр"), TableColumnMap(key="value", label="Значение")],
        rows=rows,
    )


async def _fetch_session_meta(request: Request) -> dict:
    session_id = request.query_params.get("id", "")
    if not session_id:
        return {}
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = CombatSessionsApi(client=client, base_url=settings.backend_base_url)
    return await api.get_session(session_id) or {}


_DETAIL_WIDGETS = (
    MetricWidget(key="detail_status", title="Статус", provider="combat.detail.status", order=10),
    MetricWidget(key="detail_round", title="Раунд", provider="combat.detail.round", order=20),
    MetricWidget(key="detail_alive", title="Живых", provider="combat.detail.alive", order=30),
    MetricWidget(key="detail_type", title="Тип", provider="combat.detail.type", order=40),
    TableWidget(key="detail_meta", title="Метаданные", provider="combat.detail.meta", order=50),
)


class CombatAdmin(CabinetAdmin):
    key = "combat"
    label = "Бой"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/admin/combat"
    order = 50
    sidebar = (
        SidebarItem(key="dashboard", label="Дашборд", path="/admin/combat", order=10),
        SidebarItem(key="sessions", label="Активные бои", path="/admin/combat/sessions", order=20),
        SidebarItem(key="analytics", label="Аналитика", path="/admin/combat/analytics", order=30),
    )
    dashboard_widgets = (
        MetricWidget(key="active_combats", title="Активных боёв", provider="combat.active", order=10),
        MetricWidget(key="completed_combats", title="Завершённых в БД", provider="combat.completed", order=20),
        MetricWidget(key="total_combats", title="Всего боёв", provider="combat.total", order=30),
        TableWidget(key="recent_combats", title="Последние бои", provider="combat.recent", order=40),
    )
    sub_pages = {
        "sessions": (TableWidget(key="combat_sessions", title="Активные бои", provider="combat.sessions", order=10),),
        "analytics": (ListWidget(key="combat_analytics", title="Аналитика", provider="combat.analytics", order=10),),
    }
    action_routes = {
        "session-detail": ("GET", "handle_session_detail"),
    }
    providers = {
        "combat.active": _active_provider,
        "combat.completed": _completed_provider,
        "combat.total": _total_provider,
        "combat.recent": _recent_provider,
        "combat.sessions": _sessions_provider,
        "combat.analytics": _analytics_provider,
        "combat.detail.status": _detail_status_provider,
        "combat.detail.round": _detail_round_provider,
        "combat.detail.alive": _detail_alive_provider,
        "combat.detail.type": _detail_type_provider,
        "combat.detail.meta": _detail_meta_provider,
    }

    async def handle_session_detail(self, request: Request) -> Response:
        session_id = request.query_params.get("id", "")
        short_id = session_id[:12] + "…" if len(session_id) > 12 else session_id
        active_admin = resolve_active_admin(request.url.path, cabinet_site.registry, _MOUNT_PATH)
        layout = build_layout_map(
            cabinet_site.registry,
            mount_path=_MOUNT_PATH,
            active_admin=active_admin,
            active_path=str(request.url.path),
            title=f"Бой {short_id}",
        )
        widgets = await resolve_admin_widgets(self, _DETAIL_WIDGETS, request)
        return cabinet_site.templates.TemplateResponse(
            request,
            "cabinet/module.html",
            {
                "layout": layout,
                "module": self,
                "module_context": {},
                "widgets": widgets,
            },
        )


cabinet_site.register(CombatAdmin)
