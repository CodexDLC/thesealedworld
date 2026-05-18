import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_cabinet.messaging.bridge import MessagingActionResult
from fastapi_cabinet.messaging.types import RegistrationStatus


@pytest.mark.unit
class TestSiteMessagingBridge:
    @pytest.fixture
    def repo(self):
        return AsyncMock()

    @pytest.fixture
    def bridge(self, repo):
        from src.frontend.features.cabinet.modules.messaging.bridge import SiteMessagingBridge
        return SiteMessagingBridge(repo=repo)

    @pytest.fixture
    def request_mock(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_registration_list_returns_pending_users(self, bridge, repo, request_mock):
        user = MagicMock(
            id=uuid.uuid4(),
            email="player@example.com",
            tester_status="pending",
            created_at=datetime(2026, 5, 15, 10, 30, tzinfo=UTC),
        )
        repo.get_pending_testers.return_value = [user]

        state = await bridge.get_registration_list_state(request=request_mock)

        assert len(state.rows) == 1
        assert state.rows[0].email == "player@example.com"
        assert state.rows[0].status == RegistrationStatus.PENDING
        assert state.pending_count == 1

    @pytest.mark.asyncio
    async def test_registration_list_empty_when_no_pending(self, bridge, repo, request_mock):
        repo.get_pending_testers.return_value = []

        state = await bridge.get_registration_list_state(request=request_mock)

        assert len(state.rows) == 0
        assert state.pending_count == 0

    @pytest.mark.asyncio
    async def test_approve_registration_changes_status(self, bridge, repo, request_mock):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="pending")
        repo.get_by_id.return_value = user

        result = await bridge.approve_registration(request=request_mock, request_id=str(user_id))

        assert result.ok is True
        repo.update_tester_status.assert_awaited_once()
        call_args = repo.update_tester_status.call_args
        assert call_args[0][0] == user_id
        assert call_args[0][1] == "approved"
        assert call_args[1]["approved_at"] is not None
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_sets_tester_approved_at(self, bridge, repo, request_mock):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="pending")
        repo.get_by_id.return_value = user

        before = datetime.now(UTC)
        await bridge.approve_registration(request=request_mock, request_id=str(user_id))

        call_args = repo.update_tester_status.call_args
        approved_at = call_args[1]["approved_at"]
        assert approved_at >= before

    @pytest.mark.asyncio
    async def test_deny_registration_changes_status(self, bridge, repo, request_mock):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="pending")
        repo.get_by_id.return_value = user

        result = await bridge.deny_registration(request=request_mock, request_id=str(user_id))

        assert result.ok is True
        repo.update_tester_status.assert_awaited_once_with(user_id, "denied")
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_user_not_found_returns_error(self, bridge, repo, request_mock):
        repo.get_by_id.return_value = None

        result = await bridge.approve_registration(request=request_mock, request_id=str(uuid.uuid4()))

        assert result.ok is False
        repo.update_tester_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approve_already_approved_returns_error(self, bridge, repo, request_mock):
        user_id = uuid.uuid4()
        user = MagicMock(id=user_id, tester_status="approved")
        repo.get_by_id.return_value = user

        result = await bridge.approve_registration(request=request_mock, request_id=str(user_id))

        assert result.ok is False
        repo.update_tester_status.assert_not_awaited()
