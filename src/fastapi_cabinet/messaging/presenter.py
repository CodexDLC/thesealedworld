from __future__ import annotations

from fastapi_cabinet.contracts.widgets import TableColumnMap, TableWidgetMap
from fastapi_cabinet.messaging.types import InboxListState, MailingListState, RegistrationListState


class MessagingCabinetPresenter:
    def inbox_widget(self, state: InboxListState) -> TableWidgetMap:
        return TableWidgetMap(
            key="inbox_list",
            title="Входящие сообщения",
            columns=[
                TableColumnMap(key="subject", label="Тема"),
                TableColumnMap(key="event_type", label="Тип"),
                TableColumnMap(key="read_label", label="Статус"),
                TableColumnMap(key="created_at", label="Дата", align="right"),
            ],
            rows=[
                {
                    "subject": msg.subject,
                    "event_type": msg.event_type,
                    "read_label": "Прочитано" if msg.is_read else "Новое",
                    "created_at": msg.created_at,
                }
                for msg in state.messages
            ],
        )

    def mailing_widget(self, state: MailingListState) -> TableWidgetMap:
        return TableWidgetMap(
            key="mailing_list",
            title="Рассылки",
            columns=[
                TableColumnMap(key="subject", label="Тема"),
                TableColumnMap(key="status", label="Статус"),
                TableColumnMap(key="recipient_count", label="Получатели", align="right"),
                TableColumnMap(key="sent_at", label="Отправлено", align="right"),
            ],
            rows=[
                {
                    "subject": row.subject,
                    "status": row.status,
                    "recipient_count": str(row.recipient_count),
                    "sent_at": row.sent_at or "—",
                }
                for row in state.rows
            ],
        )

    def registration_widget(self, state: RegistrationListState) -> TableWidgetMap:
        return TableWidgetMap(
            key="registration_list",
            title="Заявки на регистрацию",
            columns=[
                TableColumnMap(key="email", label="Email"),
                TableColumnMap(key="username", label="Username"),
                TableColumnMap(key="status", label="Статус"),
                TableColumnMap(key="submitted_at", label="Дата подачи", align="right"),
            ],
            rows=[
                {
                    "email": row.email,
                    "username": row.username,
                    "status": row.status,
                    "submitted_at": row.submitted_at,
                }
                for row in state.rows
            ],
        )


__all__ = ["MessagingCabinetPresenter"]
