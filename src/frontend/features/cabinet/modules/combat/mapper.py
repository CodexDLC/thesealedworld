from fastapi_cabinet.contracts.widgets import MetricWidgetMap, TableColumnMap, TableWidgetMap
from src.frontend.features.cabinet.modules.combat.service import CombatStats
from src.frontend.integrations.backend_api.game_config import ConfigEntryDTO


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

    def settings_table(self, entries: list[ConfigEntryDTO]) -> TableWidgetMap:
        rows = [
            {
                "key": e.key,
                "current": e.current,
                "default": e.default,
                "type": e.value_type,
                "modified": "✎" if e.is_modified else "",
            }
            for e in entries
        ]
        return TableWidgetMap(
            key="combat_settings",
            title="Настройки боя (Redis)",
            columns=[
                TableColumnMap(key="modified", label=""),
                TableColumnMap(key="key", label="Параметр"),
                TableColumnMap(key="current", label="Текущее"),
                TableColumnMap(key="default", label="По умолчанию"),
                TableColumnMap(key="type", label="Тип"),
            ],
            rows=rows,
        )
