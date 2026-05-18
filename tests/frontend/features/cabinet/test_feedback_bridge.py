import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.cabinet.modules.feedback.bridge import SiteFeedbackBridge


@pytest.mark.unit
class TestSiteFeedbackBridge:
    @pytest.fixture
    def repo(self):
        return AsyncMock()

    @pytest.fixture
    def bridge(self, repo):
        return SiteFeedbackBridge(repo=repo)

    @pytest.fixture
    def request_mock(self):
        return MagicMock()

    def _make_feedback(self, *, fb_id=1, fb_type="bug", status="new"):
        return MagicMock(
            id=fb_id,
            user_id=uuid.uuid4(),
            type=fb_type,
            title="Test feedback",
            body="Detailed description",
            status=status,
            priority="critical" if fb_type == "bug" else None,
            created_at=datetime(2026, 5, 15, 10, 30, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_returns_all_feedback(self, bridge, repo, request_mock):
        repo.get_all.return_value = [self._make_feedback(), self._make_feedback(fb_id=2, fb_type="wish")]

        state = await bridge.get_feedback_list_state(request=request_mock)

        assert len(state.rows) == 2
        assert state.total_count == 2
        repo.get_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_filters_by_type(self, bridge, repo, request_mock):
        repo.get_by_type.return_value = [self._make_feedback()]

        state = await bridge.get_feedback_list_state(request=request_mock, type_filter="bug")

        assert len(state.rows) == 1
        repo.get_by_type.assert_awaited_once_with("bug")

    @pytest.mark.asyncio
    async def test_new_count_tracks_new_status(self, bridge, repo, request_mock):
        repo.get_all.return_value = [
            self._make_feedback(status="new"),
            self._make_feedback(fb_id=2, status="read"),
            self._make_feedback(fb_id=3, status="new"),
        ]

        state = await bridge.get_feedback_list_state(request=request_mock)

        assert state.new_count == 2

    @pytest.mark.asyncio
    async def test_update_status_changes_record(self, bridge, repo, request_mock):
        repo.get_by_id.return_value = self._make_feedback()
        repo.update_status = AsyncMock()
        repo.commit = AsyncMock()

        result = await bridge.update_feedback_status(request=request_mock, feedback_id="1", status="read")

        assert result.ok is True
        repo.update_status.assert_awaited_once_with(1, "read")
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, bridge, repo, request_mock):
        repo.get_by_id.return_value = None

        result = await bridge.update_feedback_status(request=request_mock, feedback_id="999", status="read")

        assert result.ok is False
