from __future__ import annotations

from typing import TYPE_CHECKING

from src.frontend.features.account.view_models.profile_vm import AccountProfileVM
from src.shared.exceptions import BusinessLogicException

if TYPE_CHECKING:
    import uuid

    from src.frontend.features.auth.dto.user import UserResponse
    from src.frontend.features.auth.repositories.user_repository import UserRepository


class AccountService:
    def __init__(self, repo: UserRepository | None = None) -> None:
        self._repo = repo

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
