import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.frontend.features.surveys.routes.pages import router


def _make_app(user=None):
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates
    from src.frontend.config.settings import settings

    app = FastAPI()
    app.include_router(router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    app.state.templates = templates

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.user = user
        request.state.game_menu_service = None
        return await call_next(request)

    return app


def _make_question(*, q_id=1, text="How was it?", q_type="text", choices=None):
    q = MagicMock(id=q_id, text=text, question_type=q_type, order=0)
    q.choices_json = json.dumps(choices) if choices else None
    return q


def _make_survey(*, title="Test Survey", questions=None):
    survey = MagicMock(title=title, description="A test survey")
    survey.questions = questions or [_make_question()]
    return survey


def _make_send(*, token="test-token-123", has_response=False):
    send = MagicMock(
        token=token,
        survey=_make_survey(),
    )
    send.response = MagicMock() if has_response else None
    return send


@pytest.mark.unit
class TestSurveyRoutes:
    @patch("src.frontend.features.surveys.routes.pages.get_db")
    @patch("src.frontend.features.surveys.routes.pages.SurveyRepository")
    def test_survey_page_renders_for_valid_token(self, MockRepo, mock_get_db):
        app = _make_app()
        mock_get_db.return_value = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_send_by_token.return_value = _make_send()
        MockRepo.return_value = mock_repo

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/survey/test-token-123")
        assert response.status_code == 200

    @patch("src.frontend.features.surveys.routes.pages.get_db")
    @patch("src.frontend.features.surveys.routes.pages.SurveyRepository")
    def test_survey_page_404_for_invalid_token(self, MockRepo, mock_get_db):
        app = _make_app()
        mock_get_db.return_value = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_send_by_token.return_value = None
        MockRepo.return_value = mock_repo

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/survey/invalid-token")
        assert response.status_code == 404

    @patch("src.frontend.features.surveys.routes.pages.get_db")
    @patch("src.frontend.features.surveys.routes.pages.SurveyRepository")
    def test_survey_shows_thanks_if_already_completed(self, MockRepo, mock_get_db):
        app = _make_app()
        mock_get_db.return_value = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_send_by_token.return_value = _make_send(has_response=True)
        MockRepo.return_value = mock_repo

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/survey/test-token-123")
        assert response.status_code == 200
        assert "Спасибо" in response.text

    def test_account_surveys_redirects_anonymous(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/surveys", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]
