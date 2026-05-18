import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.feedback.dto.feedback_dto import FeedbackCreate
from src.frontend.features.feedback.services.feedback_service import FeedbackService
from src.shared.exceptions import BusinessLogicException


@pytest.mark.unit
class TestFeedbackService:
    @pytest.fixture
    def repo(self):
        repo = AsyncMock()
        repo.create = AsyncMock(side_effect=lambda f: f)
        repo.commit = AsyncMock()
        repo.get_by_user = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def service(self, repo):
        return FeedbackService(repo=repo)

    @pytest.mark.asyncio
    async def test_submit_feedback_creates_record(self, service, repo):
        data = FeedbackCreate(type="bug", title="Crash on login", body="Game crashes when I press login button", priority="critical")

        result = await service.submit(user_id=uuid.uuid4(), tester_status="approved", data=data)

        assert result.type == "bug"
        assert result.title == "Crash on login"
        assert result.status == "new"
        repo.create.assert_awaited_once()
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_feedback_rejects_non_tester(self, service):
        data = FeedbackCreate(type="wish", title="Add more quests", body="I want more quests in the game")

        with pytest.raises(BusinessLogicException):
            await service.submit(user_id=uuid.uuid4(), tester_status="none", data=data)

    @pytest.mark.asyncio
    async def test_submit_feedback_rejects_pending_tester(self, service):
        data = FeedbackCreate(type="wish", title="Add more quests", body="I want more quests in the game")

        with pytest.raises(BusinessLogicException):
            await service.submit(user_id=uuid.uuid4(), tester_status="pending", data=data)

    @pytest.mark.asyncio
    async def test_submit_priority_only_for_bugs(self, service):
        data = FeedbackCreate(type="wish", title="Better UI please", body="The UI could use some improvements", priority="critical")

        with pytest.raises(BusinessLogicException):
            await service.submit(user_id=uuid.uuid4(), tester_status="approved", data=data)

    @pytest.mark.asyncio
    async def test_list_user_feedback_returns_own_only(self, service, repo):
        user_id = uuid.uuid4()
        await service.list_user_feedback(user_id)
        repo.get_by_user.assert_awaited_once_with(user_id)


@pytest.mark.unit
class TestFeedbackDTO:
    def test_feedback_create_validates_type(self):
        with pytest.raises(Exception):
            FeedbackCreate(type="invalid", title="Test", body="Test body text here")

    def test_feedback_create_validates_title_length(self):
        with pytest.raises(Exception):
            FeedbackCreate(type="bug", title="AB", body="Test body text here")

    def test_feedback_create_validates_body_length(self):
        with pytest.raises(Exception):
            FeedbackCreate(type="bug", title="Valid title", body="Short")

    def test_feedback_create_validates_priority(self):
        with pytest.raises(Exception):
            FeedbackCreate(type="bug", title="Valid title", body="Valid body text content", priority="invalid_priority")

    def test_feedback_create_valid(self):
        data = FeedbackCreate(type="bug", title="Valid bug", body="This is a valid bug report")
        assert data.type == "bug"
        assert data.priority is None
