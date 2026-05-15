from fastapi import Request

from fastapi_cabinet.messaging.bridge import MessagingActionResult
from fastapi_cabinet.messaging.types import (
    InboxListState,
    InboxMessageState,
    MailingListState,
    RegistrationListState,
    RegistrationRequestState,
    RegistrationStatus,
)


class StubMessagingBridge:
    async def get_inbox_state(self, *, request: Request) -> InboxListState:
        return InboxListState(
            messages=[
                InboxMessageState(
                    id="1",
                    subject="Добро пожаловать",
                    body="Система запущена и готова к работе.",
                    event_type="system",
                    is_read=False,
                    created_at="13.05.2026 12:00",
                ),
            ],
            unread_count=1,
        )

    async def get_mailing_list_state(self, *, request: Request) -> MailingListState:
        return MailingListState(rows=[])

    async def get_registration_list_state(self, *, request: Request) -> RegistrationListState:
        return RegistrationListState(
            rows=[
                RegistrationRequestState(
                    id="1",
                    email="player@example.com",
                    username="player1",
                    status=RegistrationStatus.PENDING,
                    submitted_at="13.05.2026 11:30",
                ),
            ],
            pending_count=1,
        )

    async def approve_registration(self, *, request: Request, request_id: str) -> MessagingActionResult:
        return MessagingActionResult(ok=True, code="stub_approved", message="Stub: одобрено")

    async def deny_registration(self, *, request: Request, request_id: str) -> MessagingActionResult:
        return MessagingActionResult(ok=True, code="stub_denied", message="Stub: отклонено")
