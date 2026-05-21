from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from fastapi_cabinet.messaging.bridge import MessagingActionResult
from fastapi_cabinet.messaging.types import (
    InboxListState,
    MailingListState,
    RegistrationListState,
    RegistrationRequestState,
    RegistrationStatus,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import Request

    from src.frontend.features.auth.repositories.user_repository import UserRepository
    from src.frontend.features.email.services.email_service import EmailService


class SiteMessagingBridge:
    def __init__(self, repo: UserRepository | None = None, *, email_service: EmailService | None = None) -> None:
        self._repo = repo
        self._email_service = email_service

    @asynccontextmanager
    async def _get_repo(self) -> AsyncGenerator[UserRepository]:
        if self._repo is not None:
            yield self._repo
            return
        from src.frontend.core.database.session import get_session_context
        from src.frontend.features.auth.repositories.user_repository import UserRepository

        async with get_session_context() as session:
            yield UserRepository(session=session)

    async def get_inbox_state(self, *, request: Request) -> InboxListState:
        return InboxListState(messages=[], unread_count=0)

    async def get_mailing_list_state(self, *, request: Request) -> MailingListState:
        return MailingListState(rows=[])

    async def get_registration_list_state(self, *, request: Request) -> RegistrationListState:
        async with self._get_repo() as repo:
            pending = await repo.get_pending_testers()
        rows = [
            RegistrationRequestState(
                id=str(user.id),
                email=user.email,
                username=user.email.split("@")[0],
                status=RegistrationStatus.PENDING,
                submitted_at=user.created_at.strftime("%d.%m.%Y %H:%M"),
            )
            for user in pending
        ]
        return RegistrationListState(rows=rows, pending_count=len(rows))

    async def approve_registration(self, *, request: Request, request_id: str) -> MessagingActionResult:
        async with self._get_repo() as repo:
            user_id = uuid.UUID(request_id)
            user = await repo.get_by_id(user_id)
            if user is None:
                return MessagingActionResult(ok=False, code="not_found", message="Пользователь не найден")
            if user.tester_status != "pending":
                return MessagingActionResult(ok=False, code="invalid_status", message="Заявка не в статусе ожидания")
            await repo.update_tester_status(user_id, "approved", approved_at=datetime.now(UTC))
            await repo.commit()
            await self._notify_status_change(email=user.email, approved=True)
        return MessagingActionResult(ok=True, code="approved", message=f"Тестер {user.email} одобрен")

    async def deny_registration(self, *, request: Request, request_id: str) -> MessagingActionResult:
        async with self._get_repo() as repo:
            user_id = uuid.UUID(request_id)
            user = await repo.get_by_id(user_id)
            if user is None:
                return MessagingActionResult(ok=False, code="not_found", message="Пользователь не найден")
            if user.tester_status != "pending":
                return MessagingActionResult(ok=False, code="invalid_status", message="Заявка не в статусе ожидания")
            await repo.update_tester_status(user_id, "denied")
            await repo.commit()
            await self._notify_status_change(email=user.email, approved=False)
        return MessagingActionResult(ok=True, code="denied", message=f"Заявка {user.email} отклонена")

    async def _notify_status_change(self, *, email: str, approved: bool) -> None:
        if self._email_service is None:
            return
        try:
            await self._email_service.send_template(
                to=email,
                subject="Заявка на тестирование одобрена" if approved else "Заявка на тестирование отклонена",
                template="tester_approved.html" if approved else "tester_denied.html",
                email=email,
            )
        except Exception:
            logger.bind(email=email).exception("TesterStatusEmailDeliveryFailed")
