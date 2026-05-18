from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_cabinet.contracts.widgets import TableColumnMap, TableWidgetMap

if TYPE_CHECKING:
    from fastapi_cabinet.feedback.types import FeedbackListState


class FeedbackCabinetPresenter:
    def feedback_widget(self, state: FeedbackListState) -> TableWidgetMap:
        return TableWidgetMap(
            key="feedback_list",
            title="Фидбек",
            columns=[
                TableColumnMap(key="type", label="Тип"),
                TableColumnMap(key="title", label="Заголовок"),
                TableColumnMap(key="email", label="Автор"),
                TableColumnMap(key="status", label="Статус"),
                TableColumnMap(key="priority", label="Приоритет"),
                TableColumnMap(key="created_at", label="Дата", align="right"),
            ],
            rows=[
                {
                    "type": row.type,
                    "title": row.title,
                    "email": row.email,
                    "status": row.status,
                    "priority": row.priority or "—",
                    "created_at": row.created_at,
                }
                for row in state.rows
            ],
        )


__all__ = ["FeedbackCabinetPresenter"]
