from fastapi import Request

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableWidgetMap
from src.frontend.site_features.cabinet.modules.combat.mapper import CombatCabinetMapper
from src.frontend.site_features.cabinet.modules.combat.service import CombatCabinetService


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


async def _settings_provider(request: Request) -> TableWidgetMap:
    entries = await CombatCabinetService().get_config(request)
    return CombatCabinetMapper().settings_table(entries)


class CombatAdmin(CabinetAdmin):
    key = "combat"
    label = "Бой"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/cabinet/combat"
    order = 10
    sidebar = (
        SidebarItem(key="dashboard", label="Дашборд", path="/cabinet/combat", order=10),
        SidebarItem(key="settings", label="Настройки боя", path="/cabinet/combat/settings", order=20),
    )
    dashboard_widgets = (
        MetricWidget(key="active_combats", title="Активных боёв", provider="combat.active", order=10),
        MetricWidget(key="completed_combats", title="Завершённых в БД", provider="combat.completed", order=20),
        MetricWidget(key="total_combats", title="Всего боёв", provider="combat.total", order=30),
        TableWidget(key="recent_combats", title="Последние бои", provider="combat.recent", order=40),
    )
    sub_pages = {
        "settings": (TableWidget(key="combat_settings", title="Настройки боя", provider="combat.settings", order=10),),
    }
    providers = {
        "combat.active": _active_provider,
        "combat.completed": _completed_provider,
        "combat.total": _total_provider,
        "combat.recent": _recent_provider,
        "combat.settings": _settings_provider,
    }


cabinet_site.register(CombatAdmin)
