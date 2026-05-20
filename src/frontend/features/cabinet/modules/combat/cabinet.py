from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import Request
from starlette.responses import Response

from fastapi_cabinet import CabinetAdmin, ChartWidget, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import ChartWidgetMap, MetricWidgetMap, TableColumnMap, TableWidgetMap
from fastapi_cabinet.rendering.layout_mapper import build_layout_map
from fastapi_cabinet.rendering.widget_mapper import resolve_admin_widgets
from fastapi_cabinet.runtime import resolve_active_admin
from src.frontend.config.settings import settings
from src.frontend.features.cabinet.modules.combat.mapper import CombatCabinetMapper
from src.frontend.features.cabinet.modules.combat.service import CombatCabinetService
from src.frontend.integrations.backend_api.combat_analytics import CombatAnalyticsApi
from src.frontend.integrations.backend_api.combat_sessions import CombatSessionsApi

_MOUNT_PATH = "/admin"
_DETAIL_URL = "/admin/combat/session-detail"

_COLORS_PIE = ["#4f46e5", "#ef4444", "#22c55e", "#f59e0b", "#0ea5e9", "#a855f7", "#ec4899"]
_COLOR_WINS = "rgba(34,197,94,0.8)"
_COLOR_LOSSES = "rgba(239,68,68,0.8)"


# ── Dashboard providers ───────────────────────────────────────────────────────


async def _active_provider(request: Request) -> MetricWidgetMap:
    stats = await CombatCabinetService().get_stats(request)
    return CombatCabinetMapper().active_metric(stats)


async def _completed_provider(request: Request) -> MetricWidgetMap:
    data = await _get_summary_data(request, days=30)
    total = data.get("total_combats", 0)
    pve = data.get("pve_total", 0)
    pvp = data.get("pvp_total", 0)
    return MetricWidgetMap(
        key="completed_combats",
        title="Завершённых (30д)",
        value=str(total),
        subtitle=f"PvE {pve} / PvP {pvp}",
    )


async def _win_rate_provider(request: Request) -> MetricWidgetMap:
    data = await _get_summary_data(request)
    rate = data.get("pve_win_rate_pct", 0.0)
    pve_total = data.get("pve_total", 0)
    return MetricWidgetMap(
        key="win_rate", title="PvE Win Rate (30д)", value=f"{rate} %", subtitle=f"{pve_total} PvE боёв"
    )


async def _avg_rounds_provider(request: Request) -> MetricWidgetMap:
    data = await _get_summary_data(request)
    avg = data.get("avg_rounds", 0.0)
    mn, mx = data.get("min_rounds", 0), data.get("max_rounds", 0)
    return MetricWidgetMap(key="avg_rounds", title="Ср. раундов (30д)", value=str(avg), subtitle=f"min {mn} / max {mx}")


async def _daily_chart_provider(request: Request) -> ChartWidgetMap:
    data = await _get_summary_data(request)
    per_day = list(reversed(data.get("combats_per_day", [])))
    labels = [row["date"] for row in per_day]
    pve_wins = [row.get("pve_wins", 0) for row in per_day]
    pve_losses = [row.get("pve_total", 0) - row.get("pve_wins", 0) for row in per_day]
    pvp = [row.get("pvp_total", 0) for row in per_day]
    return ChartWidgetMap(
        key="daily_chart",
        title="Бои по дням (30д)",
        chart_type="bar",
        labels=labels,
        datasets=[
            {"label": "PvE победы", "data": pve_wins, "backgroundColor": _COLOR_WINS, "stack": "s"},
            {"label": "PvE пораж.", "data": pve_losses, "backgroundColor": _COLOR_LOSSES, "stack": "s"},
            {"label": "PvP", "data": pvp, "backgroundColor": "rgba(99,102,241,0.7)", "stack": "p"},
        ],
        height=260,
        options={"scales": {"x": {"stacked": True}, "y": {"stacked": True}}},
        span=2,
    )


async def _recent_provider(request: Request) -> TableWidgetMap:
    data = await _get_summary_data(request, days=7)
    per_day = data.get("combats_per_day", [])[:7]
    rows = [
        {
            "date": row["date"],
            "total": row.get("total", 0),
            "pve_wins": row.get("pve_wins", 0),
            "pve_losses": row.get("pve_total", 0) - row.get("pve_wins", 0),
            "pvp": row.get("pvp_total", 0),
        }
        for row in per_day
    ]
    return TableWidgetMap(
        key="recent_combats",
        title="Бои за последние 7 дней",
        columns=[
            TableColumnMap(key="date", label="Дата"),
            TableColumnMap(key="total", label="Всего"),
            TableColumnMap(key="pve_wins", label="PvE победы"),
            TableColumnMap(key="pve_losses", label="PvE пораж."),
            TableColumnMap(key="pvp", label="PvP"),
        ],
        rows=rows,
    )


# ── Sessions provider ─────────────────────────────────────────────────────────


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


# ── Session-detail providers ──────────────────────────────────────────────────


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


# ── Analytics: data fetchers ──────────────────────────────────────────────────


async def _get_summary_data(request: Request, *, days: int = 30) -> dict:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = CombatAnalyticsApi(client=client, base_url=settings.backend_base_url)
    try:
        return await api.get_combat_summary(days=days)
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {}


async def _get_analytics_rows(request: Request, *, days: int = 30) -> list[dict]:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = CombatAnalyticsApi(client=client, base_url=settings.backend_base_url)
    date_from = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    try:
        data = await api.get_rollups(bucket_grain="day", date_from=date_from)
        return data.get("rows", [])
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []


async def _get_drilldown_data(request: Request, *, limit: int = 100, offset: int = 0) -> dict:
    client: httpx.AsyncClient = request.app.state.backend_http_client
    api = CombatAnalyticsApi(client=client, base_url=settings.backend_base_url)
    date_from = (datetime.now(UTC) - timedelta(days=30)).date().isoformat()
    try:
        return await api.get_drilldown(limit=limit, offset=offset, date_from=date_from)
    except (httpx.HTTPStatusError, httpx.RequestError):
        return {"rows": [], "limit": limit, "offset": offset}


# ── Analytics: aggregation helpers ───────────────────────────────────────────


def _aggregate_counters(rows: list[dict]) -> dict[str, Any]:
    acc: dict[str, float] = defaultdict(float)
    for row in rows:
        c = row.get("counters", {})
        for k in (
            "attempts",
            "hits",
            "crits",
            "dodges",
            "parries",
            "blocks",
            "sum_raw_damage",
            "sum_final_damage",
            "sum_armor_effective",
            "sum_armor_ignored",
        ):
            acc[k] += c.get(k) or 0
        acc["_proc_weight"] += (c.get("proc_rate") or 0) * (c.get("attempts") or 0)
    n = max(1, int(acc["attempts"]))
    raw_total = acc["sum_raw_damage"] or 0.01
    return {
        "attempts": int(acc["attempts"]),
        "hits": int(acc["hits"]),
        "crits": int(acc["crits"]),
        "dodges": int(acc["dodges"]),
        "parries": int(acc["parries"]),
        "blocks": int(acc["blocks"]),
        "hit_rate": round(acc["hits"] / n * 100, 1),
        "crit_rate": round(acc["crits"] / n * 100, 1),
        "dodge_rate": round(acc["dodges"] / n * 100, 1),
        "parry_rate": round(acc["parries"] / n * 100, 1),
        "block_rate": round(acc["blocks"] / n * 100, 1),
        "avg_raw_dmg": round(acc["sum_raw_damage"] / n, 2),
        "avg_final_dmg": round(acc["sum_final_damage"] / n, 2),
        "avg_armor_effective": round(acc["sum_armor_effective"] / n, 2),
        "armor_ignore_pct": round(acc["sum_armor_ignored"] / raw_total * 100, 1),
        "proc_rate_pct": round(acc["_proc_weight"] / n * 100, 1),
    }


def _group_and_aggregate(rows: list[dict], dim_keys: list[str]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        dims = row.get("dimensions", {})
        key = tuple(str(dims.get(k) or "—") for k in dim_keys)
        groups[key].append(row)
    result = []
    for group_key, group_rows in groups.items():
        agg = _aggregate_counters(group_rows)
        for i, k in enumerate(dim_keys):
            agg[k] = group_key[i]
        result.append(agg)
    return sorted(result, key=lambda r: r["attempts"], reverse=True)


# ── Analytics: layout helper ──────────────────────────────────────────────────


def _render_analytics_page(admin: Any, request: Request, title: str, widgets: list) -> Any:
    active_path = str(request.url.path)
    active_admin = resolve_active_admin(active_path, cabinet_site.registry, _MOUNT_PATH)
    layout = build_layout_map(
        cabinet_site.registry,
        mount_path=_MOUNT_PATH,
        active_admin=active_admin,
        active_path=active_path,
        title=title,
    )
    return cabinet_site.templates.TemplateResponse(
        request,
        "cabinet/module.html",
        {"layout": layout, "module": admin, "module_context": {}, "widgets": widgets},
    )


# ── Widget definitions (non-analytics) ───────────────────────────────────────

_DETAIL_WIDGETS = (
    MetricWidget(key="detail_status", title="Статус", provider="combat.detail.status", order=10),
    MetricWidget(key="detail_round", title="Раунд", provider="combat.detail.round", order=20),
    MetricWidget(key="detail_alive", title="Живых", provider="combat.detail.alive", order=30),
    MetricWidget(key="detail_type", title="Тип", provider="combat.detail.type", order=40),
    TableWidget(key="detail_meta", title="Метаданные", provider="combat.detail.meta", order=50),
)


# ── Admin class ───────────────────────────────────────────────────────────────


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
        SidebarItem(key="analytics", label="Обзор", path="/admin/combat/analytics", order=30),
        SidebarItem(key="a-weapon", label="По оружию", path="/admin/combat/analytics-weapon", order=40),
        SidebarItem(key="a-armor", label="По броне", path="/admin/combat/analytics-armor", order=50),
        SidebarItem(key="a-feint", label="Скиллы & Финты", path="/admin/combat/analytics-feint", order=60),
        SidebarItem(key="a-outcomes", label="Итоги боёв", path="/admin/combat/analytics-outcomes", order=70),
        SidebarItem(key="a-drill", label="Журнал", path="/admin/combat/analytics-drilldown", order=80),
    )
    dashboard_widgets = (
        MetricWidget(key="active_combats", title="Активных боёв", provider="combat.active", order=10),
        MetricWidget(key="completed_combats", title="Завершённых в БД", provider="combat.completed", order=20),
        MetricWidget(key="win_rate", title="Win Rate (30д)", provider="combat.win_rate", order=30),
        MetricWidget(key="avg_rounds", title="Ср. раундов (30д)", provider="combat.avg_rounds", order=40),
        ChartWidget(key="daily_chart", title="Бои по дням", provider="combat.daily_chart", chart_type="bar", order=50),
        TableWidget(key="recent_combats", title="Последние бои", provider="combat.recent", order=60),
    )
    sub_pages = {
        "sessions": (TableWidget(key="combat_sessions", title="Активные бои", provider="combat.sessions", order=10),),
    }
    action_routes = {
        "session-detail": ("GET", "handle_session_detail"),
        "analytics": ("GET", "handle_analytics_overview"),
        "analytics-weapon": ("GET", "handle_analytics_weapon"),
        "analytics-armor": ("GET", "handle_analytics_armor"),
        "analytics-feint": ("GET", "handle_analytics_feint"),
        "analytics-outcomes": ("GET", "handle_analytics_outcomes"),
        "analytics-drilldown": ("GET", "handle_analytics_drilldown"),
    }
    providers = {
        "combat.active": _active_provider,
        "combat.completed": _completed_provider,
        "combat.win_rate": _win_rate_provider,
        "combat.avg_rounds": _avg_rounds_provider,
        "combat.daily_chart": _daily_chart_provider,
        "combat.recent": _recent_provider,
        "combat.sessions": _sessions_provider,
        "combat.detail.status": _detail_status_provider,
        "combat.detail.round": _detail_round_provider,
        "combat.detail.alive": _detail_alive_provider,
        "combat.detail.type": _detail_type_provider,
        "combat.detail.meta": _detail_meta_provider,
    }

    # ── Analytics: overview ───────────────────────────────────────────────────

    async def handle_analytics_overview(self, request: Request) -> Response:
        rows = await _get_analytics_rows(request)
        agg = _aggregate_counters(rows)
        weapons = _group_and_aggregate(rows, ["weapon_base_id", "weapon_tier"])[:10]
        armors = _group_and_aggregate(rows, ["armor_class", "armor_tier"])[:10]

        outcome_labels = ["Hit", "Crit", "Dodge", "Parry", "Block", "Miss"]
        misses = max(0, agg["attempts"] - agg["hits"] - agg["dodges"] - agg["parries"] - agg["blocks"])
        outcome_values = [
            agg["hits"] - agg["crits"],
            agg["crits"],
            agg["dodges"],
            agg["parries"],
            agg["blocks"],
            misses,
        ]

        tier_groups = [r for r in _group_and_aggregate(rows, ["weapon_tier"]) if r["weapon_tier"] != "—"]
        tier_labels = [f"Тир {r['weapon_tier']}" for r in tier_groups]
        tier_values = [r["avg_final_dmg"] for r in tier_groups]

        bt_groups = _group_and_aggregate(rows, ["battle_type"])
        bt_labels = [r["battle_type"] for r in bt_groups]
        bt_attempts = [r["attempts"] for r in bt_groups]
        bt_hit_rates = [r["hit_rate"] for r in bt_groups]

        widgets: list = [
            MetricWidgetMap(key="m_attempts", title="Всего попыток", value=str(agg["attempts"]), subtitle="за 30 дней"),
            MetricWidgetMap(key="m_hit", title="Hit %", value=f"{agg['hit_rate']} %", subtitle=f"хитов {agg['hits']}"),
            MetricWidgetMap(
                key="m_crit", title="Crit %", value=f"{agg['crit_rate']} %", subtitle=f"критов {agg['crits']}"
            ),
            MetricWidgetMap(
                key="m_dodge", title="Dodge %", value=f"{agg['dodge_rate']} %", subtitle=f"уклонов {agg['dodges']}"
            ),
            ChartWidgetMap(
                key="bt_split",
                title="Атак по типу боя (PvE / PvP)",
                chart_type="bar",
                labels=bt_labels,
                datasets=[
                    {"label": "Попыток", "data": bt_attempts, "backgroundColor": "rgba(99,102,241,0.8)"},
                    {"label": "Hit %", "data": bt_hit_rates, "backgroundColor": "rgba(34,197,94,0.6)"},
                ],
                height=240,
                span=2,
            ),
            ChartWidgetMap(
                key="outcome_pie",
                title="Распределение исходов",
                chart_type="pie",
                labels=outcome_labels,
                datasets=[{"data": outcome_values, "backgroundColor": _COLORS_PIE}],
                height=260,
            ),
            ChartWidgetMap(
                key="damage_by_tier",
                title="Ср. урон по тиру оружия",
                chart_type="bar",
                labels=tier_labels,
                datasets=[{"label": "Ср. итог. урон", "data": tier_values, "backgroundColor": "rgba(99,102,241,0.8)"}],
                height=260,
                span=2,
            ),
            TableWidgetMap(
                key="top_weapons",
                title="Топ-10 оружий",
                columns=[
                    TableColumnMap(key="weapon_base_id", label="Оружие"),
                    TableColumnMap(key="weapon_tier", label="Тир"),
                    TableColumnMap(key="attempts", label="Попыток"),
                    TableColumnMap(key="hit_rate", label="Hit %"),
                    TableColumnMap(key="crit_rate", label="Crit %"),
                    TableColumnMap(key="avg_raw_dmg", label="Ср. сырой"),
                    TableColumnMap(key="avg_final_dmg", label="Ср. итог."),
                ],
                rows=weapons,
            ),
            TableWidgetMap(
                key="top_armor",
                title="Топ-10 брони",
                columns=[
                    TableColumnMap(key="armor_class", label="Броня"),
                    TableColumnMap(key="armor_tier", label="Тир"),
                    TableColumnMap(key="attempts", label="Атак"),
                    TableColumnMap(key="block_rate", label="Block %"),
                    TableColumnMap(key="avg_armor_effective", label="Ср. поглощение"),
                    TableColumnMap(key="armor_ignore_pct", label="Пробитий %"),
                ],
                rows=armors,
            ),
        ]
        return _render_analytics_page(self, request, "Аналитика боя — Обзор", widgets)

    # ── Analytics: weapon breakdown ───────────────────────────────────────────

    async def handle_analytics_weapon(self, request: Request) -> Response:
        rows = await _get_analytics_rows(request)
        weapons = _group_and_aggregate(rows, ["weapon_base_id", "weapon_tier"])
        top15 = weapons[:15]
        weapon_labels = [f"{r['weapon_base_id']} (т{r['weapon_tier']})" for r in top15]
        hit_values = [r["hit_rate"] for r in top15]
        usage_values = [r["attempts"] for r in top15]

        # PvE vs PvP split for top-10 weapons
        pve_rows = [r for r in rows if (r.get("dimensions") or {}).get("battle_type") not in ("pvp", "shadow", "arena")]
        pvp_rows = [r for r in rows if (r.get("dimensions") or {}).get("battle_type") in ("pvp", "shadow", "arena")]
        pve_weapons = _group_and_aggregate(pve_rows, ["weapon_base_id", "weapon_tier"])[:10]
        pvp_weapons = _group_and_aggregate(pvp_rows, ["weapon_base_id", "weapon_tier"])[:10]
        pve_w_labels = [f"{r['weapon_base_id']}" for r in pve_weapons]
        pvp_w_labels = [f"{r['weapon_base_id']}" for r in pvp_weapons]

        most_used = weapons[0] if weapons else {}
        best_hit = max(weapons, key=lambda r: r["hit_rate"], default={})

        widgets: list = [
            MetricWidgetMap(
                key="w_most_used",
                title="Топ по использованию",
                value=str(most_used.get("weapon_base_id", "—")),
                subtitle=f"тир {most_used.get('weapon_tier', '—')}, {most_used.get('attempts', 0)} попыток",
            ),
            MetricWidgetMap(
                key="w_best_hit",
                title="Лучший Hit Rate",
                value=f"{best_hit.get('hit_rate', 0)} %",
                subtitle=str(best_hit.get("weapon_base_id", "—")),
            ),
            ChartWidgetMap(
                key="weapon_hit_chart",
                title="Hit Rate по оружию (топ-15)",
                chart_type="bar",
                labels=weapon_labels,
                datasets=[{"label": "Hit %", "data": hit_values, "backgroundColor": "rgba(99,102,241,0.8)"}],
                height=280,
                span=2,
            ),
            ChartWidgetMap(
                key="weapon_usage_pie",
                title="Доля использования по оружию",
                chart_type="doughnut",
                labels=weapon_labels,
                datasets=[{"data": usage_values, "backgroundColor": (_COLORS_PIE * 3)[: len(weapon_labels)]}],
                height=280,
            ),
            ChartWidgetMap(
                key="weapon_pve_chart",
                title="PvE — топ-10 оружий (попыток)",
                chart_type="bar",
                labels=pve_w_labels,
                datasets=[
                    {
                        "label": "PvE попыток",
                        "data": [r["attempts"] for r in pve_weapons],
                        "backgroundColor": _COLOR_WINS,
                    }
                ],
                height=240,
                span=2,
            ),
            ChartWidgetMap(
                key="weapon_pvp_chart",
                title="PvP — топ-10 оружий (попыток)",
                chart_type="bar",
                labels=pvp_w_labels,
                datasets=[
                    {
                        "label": "PvP попыток",
                        "data": [r["attempts"] for r in pvp_weapons],
                        "backgroundColor": "rgba(99,102,241,0.8)",
                    }
                ],
                height=240,
                span=2,
            ),
            TableWidgetMap(
                key="weapon_breakdown",
                title=f"Все оружия — {len(weapons)} позиций",
                columns=[
                    TableColumnMap(key="weapon_base_id", label="Оружие"),
                    TableColumnMap(key="weapon_tier", label="Тир"),
                    TableColumnMap(key="attempts", label="Попыток"),
                    TableColumnMap(key="hit_rate", label="Hit %"),
                    TableColumnMap(key="crit_rate", label="Crit %"),
                    TableColumnMap(key="dodge_rate", label="Dodge %"),
                    TableColumnMap(key="avg_raw_dmg", label="Ср. сырой"),
                    TableColumnMap(key="avg_final_dmg", label="Ср. итог."),
                    TableColumnMap(key="armor_ignore_pct", label="Проб %"),
                    TableColumnMap(key="proc_rate_pct", label="Proc %"),
                ],
                rows=weapons,
            ),
        ]
        return _render_analytics_page(self, request, "Аналитика: по оружию", widgets)

    # ── Analytics: armor breakdown ────────────────────────────────────────────

    async def handle_analytics_armor(self, request: Request) -> Response:
        rows = await _get_analytics_rows(request)
        armors = _group_and_aggregate(rows, ["armor_class", "armor_tier"])
        top15 = armors[:15]
        armor_labels = [f"{r['armor_class']} (т{r['armor_tier']})" for r in top15]
        absorb_values = [r["avg_armor_effective"] for r in top15]
        usage_values = [r["attempts"] for r in top15]

        best_absorb = max(armors, key=lambda r: r["avg_armor_effective"], default={})
        avg_block = round(sum(r["block_rate"] for r in armors) / max(1, len(armors)), 1) if armors else 0.0

        widgets: list = [
            MetricWidgetMap(
                key="a_best_absorb",
                title="Лучшее поглощение",
                value=f"{best_absorb.get('avg_armor_effective', 0):.2f}",
                subtitle=str(best_absorb.get("armor_class", "—")),
            ),
            MetricWidgetMap(
                key="a_avg_block",
                title="Ср. Block Rate",
                value=f"{avg_block} %",
                subtitle=f"{len(armors)} типов брони",
            ),
            ChartWidgetMap(
                key="armor_absorb_chart",
                title="Ср. поглощение по классу брони",
                chart_type="bar",
                labels=armor_labels,
                datasets=[
                    {"label": "Ср. поглощение", "data": absorb_values, "backgroundColor": "rgba(14,165,233,0.8)"}
                ],
                height=280,
                span=2,
            ),
            ChartWidgetMap(
                key="armor_usage_pie",
                title="Доля брони по типу",
                chart_type="doughnut",
                labels=armor_labels,
                datasets=[{"data": usage_values, "backgroundColor": (_COLORS_PIE * 3)[: len(armor_labels)]}],
                height=280,
            ),
            TableWidgetMap(
                key="armor_breakdown",
                title=f"Все типы брони — {len(armors)} позиций",
                columns=[
                    TableColumnMap(key="armor_class", label="Класс брони"),
                    TableColumnMap(key="armor_tier", label="Тир"),
                    TableColumnMap(key="attempts", label="Атак"),
                    TableColumnMap(key="hit_rate", label="Hit %"),
                    TableColumnMap(key="block_rate", label="Block %"),
                    TableColumnMap(key="avg_armor_effective", label="Ср. поглощение"),
                    TableColumnMap(key="armor_ignore_pct", label="Пробитий %"),
                    TableColumnMap(key="avg_final_dmg", label="Ср. итог. урон"),
                ],
                rows=armors,
            ),
        ]
        return _render_analytics_page(self, request, "Аналитика: по броне", widgets)

    # ── Analytics: feints & triggers ──────────────────────────────────────────

    async def handle_analytics_feint(self, request: Request) -> Response:
        rows = await _get_analytics_rows(request)
        feints = _group_and_aggregate(rows, ["feint_id"])
        triggers = _group_and_aggregate(rows, ["trigger_id"])

        valid_feints = [r for r in feints[:15] if r["feint_id"] != "—"]
        valid_triggers = [r for r in triggers[:15] if r["trigger_id"] != "—"]
        feint_labels = [r["feint_id"] for r in valid_feints]
        feint_counts = [r["attempts"] for r in valid_feints]
        trigger_labels = [r["trigger_id"] for r in valid_triggers]
        proc_values = [r["proc_rate_pct"] for r in valid_triggers]

        top_feint = feints[0] if feints else {}
        top_trigger = triggers[0] if triggers else {}

        widgets: list = [
            MetricWidgetMap(
                key="f_top",
                title="Топ финт",
                value=str(top_feint.get("feint_id", "—")),
                subtitle=f"{top_feint.get('attempts', 0)} попыток",
            ),
            MetricWidgetMap(
                key="t_top",
                title="Топ триггер",
                value=str(top_trigger.get("trigger_id", "—")),
                subtitle=f"Proc {top_trigger.get('proc_rate_pct', 0)} %",
            ),
            ChartWidgetMap(
                key="feint_chart",
                title="Частота использования финтов",
                chart_type="bar",
                labels=feint_labels,
                datasets=[{"label": "Попыток", "data": feint_counts, "backgroundColor": "rgba(99,102,241,0.8)"}],
                height=260,
                span=2,
            ),
            ChartWidgetMap(
                key="trigger_chart",
                title="Proc Rate триггеров",
                chart_type="bar",
                labels=trigger_labels,
                datasets=[{"label": "Proc %", "data": proc_values, "backgroundColor": "rgba(239,68,68,0.8)"}],
                height=260,
                span=2,
            ),
            TableWidgetMap(
                key="feints",
                title=f"Финты — {len(feints)} позиций",
                columns=[
                    TableColumnMap(key="feint_id", label="Финт"),
                    TableColumnMap(key="attempts", label="Попыток"),
                    TableColumnMap(key="hit_rate", label="Hit %"),
                    TableColumnMap(key="crit_rate", label="Crit %"),
                    TableColumnMap(key="avg_final_dmg", label="Ср. урон"),
                ],
                rows=feints,
            ),
            TableWidgetMap(
                key="triggers",
                title=f"Триггеры — {len(triggers)} позиций",
                columns=[
                    TableColumnMap(key="trigger_id", label="Триггер"),
                    TableColumnMap(key="attempts", label="Попыток"),
                    TableColumnMap(key="proc_rate_pct", label="Proc %"),
                    TableColumnMap(key="hit_rate", label="Hit %"),
                    TableColumnMap(key="avg_final_dmg", label="Ср. урон"),
                ],
                rows=triggers,
            ),
        ]
        return _render_analytics_page(self, request, "Аналитика: финты & триггеры", widgets)

    # ── Analytics: combat outcomes (from CombatFinalization) ─────────────────

    async def handle_analytics_outcomes(self, request: Request) -> Response:
        data = await _get_summary_data(request, days=30)
        per_day = list(reversed(data.get("combats_per_day", [])))
        win_stats = data.get("win_stats", [])

        labels = [row["date"] for row in per_day]
        pve_wins = [row.get("pve_wins", 0) for row in per_day]
        pve_losses = [row.get("pve_total", 0) - row.get("pve_wins", 0) for row in per_day]
        pvp_vals = [row.get("pvp_total", 0) for row in per_day]

        total_combats = data.get("total_combats", 0)
        pve_total = data.get("pve_total", 0)
        pvp_total = data.get("pvp_total", 0)
        total_pve_wins = sum(pve_wins)
        total_pve_losses = sum(pve_losses)

        table_rows: list[dict] = []
        for group in win_stats:
            bt = group.get("battle_type", "—")
            total_g = group.get("total", 0)
            for team, cnt in sorted((group.get("team_wins") or {}).items(), key=lambda x: -x[1]):
                table_rows.append(
                    {
                        "battle_type": bt,
                        "winner_team": team,
                        "wins": cnt,
                        "total": total_g,
                        "win_rate_pct": round(cnt / total_g * 100, 1) if total_g > 0 else 0.0,
                    }
                )

        widgets: list = [
            MetricWidgetMap(
                key="o_pve_winrate",
                title="PvE Win Rate",
                value=f"{data.get('pve_win_rate_pct', 0.0)} %",
                subtitle=f"{pve_total} PvE боёв",
            ),
            MetricWidgetMap(
                key="o_rounds",
                title="Ср. раундов",
                value=str(data.get("avg_rounds", 0.0)),
                subtitle=f"min {data.get('min_rounds', 0)} / max {data.get('max_rounds', 0)}",
            ),
            MetricWidgetMap(
                key="o_pve_total",
                title="PvE боёв (30д)",
                value=str(pve_total),
                subtitle=f"победы {total_pve_wins} / пораж. {total_pve_losses}",
            ),
            MetricWidgetMap(
                key="o_pvp_total",
                title="PvP боёв (30д)",
                value=str(pvp_total),
                subtitle=f"всего {total_combats} боёв",
            ),
            ChartWidgetMap(
                key="wins_per_day",
                title="Бои по дням (PvE победы / пораж. / PvP)",
                chart_type="bar",
                labels=labels,
                datasets=[
                    {"label": "PvE победы", "data": pve_wins, "backgroundColor": _COLOR_WINS, "stack": "s"},
                    {"label": "PvE пораж.", "data": pve_losses, "backgroundColor": _COLOR_LOSSES, "stack": "s"},
                    {"label": "PvP", "data": pvp_vals, "backgroundColor": "rgba(99,102,241,0.7)", "stack": "p"},
                ],
                height=280,
                options={"scales": {"x": {"stacked": True}, "y": {"stacked": True}}},
                span=2,
            ),
            ChartWidgetMap(
                key="pve_pie",
                title="PvE — победы / поражения",
                chart_type="pie",
                labels=["PvE победы", "PvE поражения"],
                datasets=[
                    {"data": [total_pve_wins, total_pve_losses], "backgroundColor": [_COLOR_WINS, _COLOR_LOSSES]}
                ],
                height=260,
            ),
            TableWidgetMap(
                key="outcomes_by_team",
                title="Победы по команде и типу боя",
                columns=[
                    TableColumnMap(key="battle_type", label="Тип боя"),
                    TableColumnMap(key="winner_team", label="Команда"),
                    TableColumnMap(key="wins", label="Побед"),
                    TableColumnMap(key="total", label="Всего боёв"),
                    TableColumnMap(key="win_rate_pct", label="Win Rate %"),
                ],
                rows=table_rows,
            ),
        ]
        return _render_analytics_page(self, request, "Итоги боёв", widgets)

    # ── Analytics: drilldown (paginated exchange facts) ───────────────────────

    async def handle_analytics_drilldown(self, request: Request) -> Response:
        offset = max(0, int(request.query_params.get("offset", 0)))
        data = await _get_drilldown_data(request, limit=100, offset=offset)
        exchange_rows = data.get("rows", [])
        base = "/admin/combat"

        table_rows = [
            {
                "date": (r.get("finished_at") or "")[:10],
                "combat_id": (r.get("combat_id") or "")[:16],
                "turn": r.get("turn", ""),
                "outcome": r.get("outcome", ""),
                "weapon": r.get("weapon_base_id") or "—",
                "tier": r.get("weapon_tier") if r.get("weapon_tier") is not None else "—",
                "armor": r.get("armor_class") or "—",
                "raw_dmg": round(r.get("raw_damage") or 0, 1),
                "final_dmg": round(r.get("final_damage") or 0, 1),
                "crit": "да" if r.get("is_crit") else "",
            }
            for r in exchange_rows
        ]

        widgets: list = [
            TableWidgetMap(
                key="drilldown",
                title=f"Журнал обменов — offset {offset}, показано {len(table_rows)}",
                columns=[
                    TableColumnMap(key="date", label="Дата"),
                    TableColumnMap(key="combat_id", label="Бой (ID)"),
                    TableColumnMap(key="turn", label="Ход"),
                    TableColumnMap(key="outcome", label="Исход"),
                    TableColumnMap(key="weapon", label="Оружие"),
                    TableColumnMap(key="tier", label="Тир"),
                    TableColumnMap(key="armor", label="Броня"),
                    TableColumnMap(key="raw_dmg", label="Сырой урон"),
                    TableColumnMap(key="final_dmg", label="Итог. урон"),
                    TableColumnMap(key="crit", label="Крит"),
                ],
                rows=table_rows,
            ),
        ]

        nav_rows = []
        if offset > 0:
            prev = max(0, offset - 100)
            nav_rows.append({"label": f"← Назад (offset {prev})", "href": f"{base}/analytics-drilldown?offset={prev}"})
        if len(exchange_rows) == 100:
            nav_rows.append(
                {
                    "label": f"Вперёд → (offset {offset + 100})",
                    "href": f"{base}/analytics-drilldown?offset={offset + 100}",
                }
            )
        if nav_rows:
            widgets.append(
                TableWidgetMap(
                    key="drilldown_nav",
                    title="Навигация",
                    columns=[TableColumnMap(key="label", label="")],
                    rows=nav_rows,
                    row_href_key="href",
                )
            )

        return _render_analytics_page(self, request, "Журнал обменов", widgets)

    # ── Session detail ────────────────────────────────────────────────────────

    async def handle_session_detail(self, request: Request) -> Response:
        session_id = request.query_params.get("id", "")
        short_id = session_id[:12] + "…" if len(session_id) > 12 else session_id
        active_admin = resolve_active_admin(request.url.path, cabinet_site.registry, _MOUNT_PATH)
        layout = build_layout_map(
            cabinet_site.registry,
            mount_path=_MOUNT_PATH,
            active_admin=active_admin,
            active_path=request.url.path,
            title=f"Бой {short_id}",
        )
        widgets = await resolve_admin_widgets(self, _DETAIL_WIDGETS, request)
        return cabinet_site.templates.TemplateResponse(
            request,
            "cabinet/module.html",
            {"layout": layout, "module": self, "module_context": {}, "widgets": widgets},
        )


cabinet_site.register(CombatAdmin)
