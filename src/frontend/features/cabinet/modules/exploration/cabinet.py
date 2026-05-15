from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, TableWidget, cabinet_site
from src.frontend.features.cabinet.modules._stub import stub_metric, stub_table


class ExplorationAdmin(CabinetAdmin):
    key = "exploration"
    label = "Путешествия"
    group = "game_server"
    group_label = "Гейм Сервер"
    path = "/cabinet/exploration"
    order = 30
    sidebar = (
        SidebarItem(key="dashboard", label="Дашборд", path="/cabinet/exploration", order=10),
        SidebarItem(key="encounters", label="Настройки энкаунтеров", path="/cabinet/exploration/encounters", order=20),
        SidebarItem(key="settings", label="Параметры путешествий", path="/cabinet/exploration/settings", order=30),
    )
    dashboard_widgets = (
        MetricWidget(key="active_travels", title="Активных путешествий", provider="exploration.active", order=10),
        MetricWidget(key="total_encounters", title="Энкаунтеров всего", provider="exploration.encounters", order=20),
        MetricWidget(key="events_fired", title="Событий сработало", provider="exploration.events", order=30),
        TableWidget(key="recent_travels", title="Последние путешествия", provider="exploration.recent", order=40),
    )
    sub_pages = {
        "encounters": (
            TableWidget(
                key="encounter_table", title="Таблица энкаунтеров", provider="exploration.encounter_table", order=10
            ),
            TableWidget(
                key="encounter_biomes", title="Веса по биомам", provider="exploration.encounter_biomes", order=20
            ),
        ),
        "settings": (
            TableWidget(
                key="travel_settings", title="Параметры путешествий", provider="exploration.travel_settings", order=10
            ),
            TableWidget(
                key="event_weights", title="Веса случайных событий", provider="exploration.event_weights", order=20
            ),
        ),
    }
    providers = {
        "exploration.active": stub_metric("active_travels", "Активных путешествий"),
        "exploration.encounters": stub_metric("total_encounters", "Энкаунтеров всего"),
        "exploration.events": stub_metric("events_fired", "Событий сработало"),
        "exploration.recent": stub_table(
            "recent_travels", "Последние путешествия", ["ID", "Игрок", "Локация", "Статус", "Дата"]
        ),
        "exploration.encounter_table": stub_table(
            "encounter_table", "Таблица энкаунтеров", ["Ключ", "Тип", "Вес", "Биом", "Уровень"]
        ),
        "exploration.encounter_biomes": stub_table("encounter_biomes", "Веса по биомам", ["Биом", "Вес", "Тип"]),
        "exploration.travel_settings": stub_table(
            "travel_settings", "Параметры путешествий", ["Параметр", "Значение", "Описание"]
        ),
        "exploration.event_weights": stub_table(
            "event_weights", "Веса случайных событий", ["Событие", "Вес", "Условие"]
        ),
    }


cabinet_site.register(ExplorationAdmin)
