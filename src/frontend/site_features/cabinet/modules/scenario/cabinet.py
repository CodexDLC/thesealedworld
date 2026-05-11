from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from src.frontend.site_features.cabinet.modules._stub import stub_metric, stub_table


class ScenarioAdmin(CabinetAdmin):
    key = "scenario"
    label = "Сценарии"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/cabinet/scenario"
    order = 20
    sidebar = (
        SidebarItem(key="dashboard", label="Дашборд", path="/cabinet/scenario", order=10),
        SidebarItem(key="settings", label="Настройки", path="/cabinet/scenario/settings", order=20),
    )
    dashboard_widgets = (
        MetricWidget(key="active_scenarios", title="Активных сценариев", provider="scenario.active", order=10),
        MetricWidget(key="total_scenarios", title="Всего сценариев", provider="scenario.total", order=20),
        MetricWidget(key="completed", title="Завершённых", provider="scenario.completed", order=30),
        TableWidget(key="recent", title="Последние сценарии", provider="scenario.recent", order=40),
    )
    sub_pages = {
        "settings": (
            TableWidget(
                key="scenario_gen_settings",
                title="Параметры генерации сценариев",
                provider="scenario.gen_settings",
                order=10,
            ),
            TableWidget(key="encounter_weights", title="Веса энкаунтеров", provider="scenario.enc_weights", order=20),
        ),
    }
    providers = {
        "scenario.active": stub_metric("active_scenarios", "Активных сценариев"),
        "scenario.total": stub_metric("total_scenarios", "Всего сценариев"),
        "scenario.completed": stub_metric("completed", "Завершённых"),
        "scenario.recent": stub_table("recent", "Последние сценарии", ["ID", "Тип", "Статус", "Игрок", "Дата"]),
        "scenario.gen_settings": stub_table(
            "scenario_gen_settings", "Параметры генерации", ["Параметр", "Значение", "Описание"]
        ),
        "scenario.enc_weights": stub_table("encounter_weights", "Веса энкаунтеров", ["Тип энкаунтера", "Вес", "Биом"]),
    }


cabinet_site.register(ScenarioAdmin)
