from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap
from src.frontend.site_features.cabinet.modules.combat.service import CombatSettingEntry, CombatStats


class CombatCabinetMapper:
    def active_metric(self, stats: CombatStats) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="active_combats",
            title="Активных боёв",
            value=str(stats.active),
            subtitle="Сейчас в Redis",
        )

    def completed_metric(self, stats: CombatStats) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="completed_combats",
            title="Завершённых в БД",
            value=str(stats.completed),
        )

    def total_metric(self, stats: CombatStats) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="total_combats",
            title="Всего боёв",
            value=str(stats.total),
        )

    def recent_table(self, stats: CombatStats) -> TableWidgetMap:
        return TableWidgetMap(
            key="recent_combats",
            title="Последние бои",
            columns=[
                TableColumnMap(key="combat_id", label="ID"),
                TableColumnMap(key="battle_type", label="Тип"),
                TableColumnMap(key="winner_team", label="Победитель"),
                TableColumnMap(key="finished_at", label="Дата"),
            ],
            rows=stats.recent,
        )

    def settings_table(self, entries: tuple[CombatSettingEntry, ...]) -> TableWidgetMap:
        return TableWidgetMap(
            key="combat_settings",
            title="Константы боевого движка",
            columns=[
                TableColumnMap(key="name", label="Параметр"),
                TableColumnMap(key="value", label="Значение"),
                TableColumnMap(key="source", label="Файл"),
            ],
            rows=[{"name": e.name, "value": e.value, "source": e.source} for e in entries],
        )
