import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.frontend.features.surveys.services.survey_service import SurveyService
from src.shared.exceptions import BusinessLogicException


@pytest.mark.unit
class TestSurveyService:
    @pytest.fixture
    def repo(self):
        repo = AsyncMock()
        repo.create_survey = AsyncMock(side_effect=lambda s: s)
        repo.create_send = AsyncMock(side_effect=lambda s: s)
        repo.create_response = AsyncMock(side_effect=lambda r: r)
        repo.commit = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, repo):
        return SurveyService(repo=repo)

    @pytest.mark.asyncio
    async def test_create_survey_with_questions(self, service, repo):
        questions = [
            {"text": "How was the combat?", "question_type": "text"},
            {"text": "Rate difficulty", "question_type": "scale"},
            {"text": "Favorite class?", "question_type": "choice", "choices": ["Warrior", "Mage"]},
        ]
        result = await service.create_survey(title="Alpha Test", description="First survey", questions=questions)

        assert result.title == "Alpha Test"
        assert len(result.questions) == 3
        assert result.questions[0].text == "How was the combat?"
        assert result.questions[2].choices_json is not None
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_to_user_creates_token(self, service, repo):
        result = await service.send_to_user(survey_id=1, user_id=uuid.uuid4())

        assert result.token is not None
        assert len(result.token) > 20
        repo.create_send.assert_awaited_once()
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_response_saves_answers(self, service, repo):
        send = MagicMock(id=1, response=None)
        repo.get_send_by_token.return_value = send

        result = await service.submit_response(token="abc123", answers={"q_1": "Great"})

        assert result.answers_json is not None
        repo.create_response.assert_awaited_once()
        repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_response_rejects_invalid_token(self, service, repo):
        repo.get_send_by_token.return_value = None

        with pytest.raises(BusinessLogicException):
            await service.submit_response(token="invalid", answers={"q_1": "Test"})

    @pytest.mark.asyncio
    async def test_submit_response_rejects_duplicate(self, service, repo):
        send = MagicMock(id=1, response=MagicMock())
        repo.get_send_by_token.return_value = send

        with pytest.raises(BusinessLogicException):
            await service.submit_response(token="abc123", answers={"q_1": "Test"})

    @pytest.mark.asyncio
    async def test_get_user_surveys(self, service, repo):
        repo.get_sends_for_user.return_value = []
        user_id = uuid.uuid4()

        result = await service.get_user_surveys(user_id)

        assert result == []
        repo.get_sends_for_user.assert_awaited_once_with(user_id)
