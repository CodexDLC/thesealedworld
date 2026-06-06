from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger

from src.frontend.features.account.view_models.profile_vm import AccountProfileVM, AccountReferralVM
from src.shared.exceptions import BusinessLogicException

if TYPE_CHECKING:
    from src.frontend.features.auth.dto.user import UserResponse
    from src.frontend.features.auth.models.user import User
    from src.frontend.features.auth.repositories.user_repository import UserRepository
    from src.frontend.features.email.services.email_service import EmailService

    AccountProfileUser = UserResponse | User


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

    def build_profile_vm(
        self,
        user: AccountProfileUser,
        *,
        site_base_url: str = "",
        referral_stats: dict[str, int] | None = None,
        referral_users: Sequence[AccountProfileUser] | None = None,
        email_verification_enabled: bool = False,
    ) -> AccountProfileVM:
        is_tester = user.tester_status == "approved"
        approved_at = user.tester_approved_at
        account_id = str(getattr(user, "id", "") or "")
        email_name = user.email.split("@", maxsplit=1)[0]
        display_name = email_name.replace(".", " ").replace("_", " ").strip().title() or "Игрок"
        initials = "".join(part[0] for part in display_name.split()[:2]).upper() or "И"
        code = (user.referral_code or "").strip() or "SEAL-PLAYER"
        base = site_base_url.rstrip("/") if site_base_url else ""
        link = f"{base}/register?ref={code}" if base else f"/register?ref={code}"
        stats = referral_stats or {}
        verified_at = getattr(user, "email_verified_at", None)
        return AccountProfileVM(
            account_id=account_id,
            email=user.email,
            created_at=user.created_at.strftime("%d.%m.%Y"),
            display_name=display_name,
            initials=initials,
            referral_code=code,
            referral_link=link,
            referrals_invited=int(stats.get("invited", 0)),
            referrals_active=int(stats.get("active", 0)),
            referral_bonus=int(stats.get("bonus", 0)),
            tester_status=user.tester_status,
            tester_approved_at=approved_at.strftime("%d.%m.%Y") if approved_at else None,
            is_tester=is_tester,
            can_create_character=True,
            email_verified=verified_at is not None,
            email_verified_at=verified_at.strftime("%d.%m.%Y") if verified_at else None,
            email_verification_enabled=email_verification_enabled,
            referrals=[_build_referral_vm(referral) for referral in referral_users or []],
        )

    async def apply_for_testing(self, user_id: UUID) -> None:
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


def _build_referral_vm(user: AccountProfileUser) -> AccountReferralVM:
    verified_at = getattr(user, "email_verified_at", None)
    created_at = getattr(user, "created_at", None)
    return AccountReferralVM(
        display_name=_masked_email(str(getattr(user, "email", ""))),
        joined_at=created_at.strftime("%d.%m.%Y") if created_at else "-",
        email_status="Подтверждён" if verified_at else "Не подтверждён",
        email_status_class="is-done" if verified_at else "is-pending",
        character_status="Не отслеживается",
        payment_status="Не отслеживается",
    )


def _masked_email(email: str) -> str:
    if "@" not in email:
        return email or "Игрок"
    local, domain = email.split("@", maxsplit=1)
    masked_local = f"{local[:1]}*" if len(local) <= 2 else f"{local[:2]}***"
    return f"{masked_local}@{domain}"
