import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.account.services.account_service import AccountService
from src.frontend.features.account.view_models.profile_vm import AccountProfileVM
from src.shared.exceptions import BusinessLogicException


@pytest.mark.unit
class TestAccountService:
    @pytest.fixture
    def repo(self):
        repo = AsyncMock()
        repo.update_tester_status = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.commit = AsyncMock()
        return repo

    @pytest.fixture
    def email_service(self):
        service = AsyncMock()
        service.send_template = AsyncMock()
        return service

    @pytest.fixture
    def service(self, repo, email_service):
        return AccountService(repo=repo, email_service=email_service, email_admin="admin@example.com")

    def test_build_profile_vm_for_regular_user(self, service):
        user_id = uuid.uuid4()
        user = MagicMock(
            id=user_id,
            email="player@example.com",
            tester_status="none",
            tester_approved_at=None,
            referral_code="SEAL-ABCD2345",
            created_at=datetime(2026, 5, 1, 12, 0, 0),
        )
        vm = service.build_profile_vm(
            user,
            site_base_url="https://example.test",
            referral_stats={"invited": 3, "active": 2, "bonus": 100},
        )

        assert isinstance(vm, AccountProfileVM)
        assert vm.account_id == str(user_id)
        assert vm.email == "player@example.com"
        assert vm.display_name == "Player"
        assert vm.initials == "P"
        assert vm.referral_code == "SEAL-ABCD2345"
        assert vm.referral_link == "https://example.test/register?ref=SEAL-ABCD2345"
        assert vm.referrals_invited == 3
        assert vm.referrals_active == 2
        assert vm.referral_bonus == 100
        assert vm.tester_status == "none"
        assert vm.is_tester is False
        assert vm.can_create_character is True
        assert vm.tester_approved_at is None

    def test_build_profile_vm_for_tester(self, service):
        user_id = uuid.uuid4()
        approved_at = datetime(2026, 5, 10, 14, 0, 0)
        user = MagicMock(
            id=user_id,
            email="tester@example.com",
            tester_status="approved",
            tester_approved_at=approved_at,
            referral_code="SEAL-TESTER01",
            created_at=datetime(2026, 5, 1, 12, 0, 0),
        )
        vm = service.build_profile_vm(user)

        assert vm.is_tester is True
        assert vm.can_create_character is True
        assert vm.tester_approved_at is not None

    def test_build_profile_vm_for_pending(self, service):
        user = MagicMock(
            id=uuid.uuid4(),
            email="pending@example.com",
            tester_status="pending",
            tester_approved_at=None,
            referral_code="SEAL-PENDING1",
            created_at=datetime(2026, 5, 1, 12, 0, 0),
        )
        vm = service.build_profile_vm(user)

        assert vm.tester_status == "pending"
        assert vm.is_tester is False
        assert vm.can_create_character is True

    def test_build_profile_vm_for_denied(self, service):
        user = MagicMock(
            id=uuid.uuid4(),
            email="denied@example.com",
            tester_status="denied",
            tester_approved_at=None,
            referral_code="SEAL-DENIED11",
            created_at=datetime(2026, 5, 1, 12, 0, 0),
        )
        vm = service.build_profile_vm(user)

        assert vm.tester_status == "denied"
        assert vm.is_tester is False


@pytest.mark.unit
class TestApplyForTesting:
    @pytest.fixture
    def repo(self):
        repo = AsyncMock()
        repo.update_tester_status = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.commit = AsyncMock()
        return repo

    @pytest.fixture
    def email_service(self):
        service = AsyncMock()
        service.send_template = AsyncMock()
        return service

    @pytest.fixture
    def service(self, repo, email_service):
        return AccountService(repo=repo, email_service=email_service, email_admin="admin@example.com")

    @pytest.mark.asyncio
    async def test_apply_for_testing_changes_status_to_pending(self, service, repo, email_service):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="none", email="player@example.com")
        repo.get_by_id.return_value = user

        await service.apply_for_testing(user_id)

        repo.update_tester_status.assert_awaited_once_with(user_id, "pending")
        repo.commit.assert_awaited_once()
        assert email_service.send_template.await_count == 2

    @pytest.mark.asyncio
    async def test_apply_for_testing_fails_if_already_pending(self, service, repo):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="pending", email="player@example.com")
        repo.get_by_id.return_value = user

        with pytest.raises(BusinessLogicException):
            await service.apply_for_testing(user_id)

        repo.update_tester_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_apply_for_testing_fails_if_already_approved(self, service, repo):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="approved", email="player@example.com")
        repo.get_by_id.return_value = user

        with pytest.raises(BusinessLogicException):
            await service.apply_for_testing(user_id)

        repo.update_tester_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_apply_for_testing_fails_if_user_not_found(self, service, repo):
        repo.get_by_id.return_value = None

        with pytest.raises(BusinessLogicException):
            await service.apply_for_testing(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_apply_for_testing_does_not_fail_when_email_delivery_breaks(self, repo):
        email_service = AsyncMock()
        email_service.send_template = AsyncMock(side_effect=RuntimeError("smtp unavailable"))
        service = AccountService(repo=repo, email_service=email_service, email_admin="admin@example.com")
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="none", email="player@example.com")
        repo.get_by_id.return_value = user

        await service.apply_for_testing(user_id)

        repo.update_tester_status.assert_awaited_once_with(user_id, "pending")
        repo.commit.assert_awaited_once()
