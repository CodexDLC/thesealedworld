from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.frontend.features.account.view_models.profile_vm import AccountProfileVM
from src.shared.exceptions import BusinessLogicException

if TYPE_CHECKING:
    import uuid

    from src.frontend.features.auth.dto.user import UserResponse
    from src.frontend.features.auth.repositories.user_repository import UserRepository
    from src.frontend.features.email.services.email_service import EmailService


class AccountService:
    def __init__(
        self,
        repo: UserRepository | None = None,
        *,
        email_service: EmailService | None = None,
        email_admin: str | None = None,
    ) -> None:
        self._repo = repo
        self._email_service = email_service
        self._email_admin = email_admin

    def build_profile_vm(self, user: UserResponse) -> AccountProfileVM:
        is_tester = user.tester_status == "approved"
        approved_at = user.tester_approved_at
        return AccountProfileVM(
            email=user.email,
            created_at=user.created_at.strftime("%d.%m.%Y"),
            tester_status=user.tester_status,
            tester_approved_at=approved_at.strftime("%d.%m.%Y") if approved_at else None,
            is_tester=is_tester,
            can_create_character=is_tester,
        )

    async def apply_for_testing(self, user_id: uuid.UUID) -> None:
        assert self._repo is not None
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise BusinessLogicException(detail="User not found")
        if user.tester_status != "none":
            raise BusinessLogicException(detail="Cannot apply: current status is already set")
        await self._repo.update_tester_status(user_id, "pending")
        await self._repo.commit()
        await self._notify_application_submitted(user.email)

    async def _notify_application_submitted(self, email: str) -> None:
        if self._email_service is None:
            return
        try:
            await self._email_service.send_template(
                to=email,
                subject="Заявка на тестирование получена",
                template="applicant_received.html",
                email=email,
            )
            if self._email_admin:
                await self._email_service.send_template(
                    to=self._email_admin,
                    subject="Новая заявка на тестирование",
                    template="admin_new_applicant.html",
                    email=email,
                )
        except Exception:
            logger.bind(email=email).exception("TesterApplicationEmailDeliveryFailed")
