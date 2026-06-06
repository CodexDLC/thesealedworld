import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient


def _make_app(user=None):
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates

    from src.frontend.app import inline_css
    from src.frontend.config.settings import settings
    from src.frontend.features.public_site.routes.pages import router

    app = FastAPI()
    app.include_router(router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.user = user
        request.state.game_menu_service = None
        return await call_next(request)

    return app


def _user_mock(*, tester_status="none"):
    return MagicMock(
        id=uuid.uuid4(),
        email="test@example.com",
        is_active=True,
        is_superuser=False,
        tester_status=tester_status,
        tester_approved_at=None,
        created_at=datetime(2026, 5, 1),
    )


@pytest.mark.unit
class TestLandingFeedbackBlock:
    def test_feedback_block_for_anonymous_links_to_support_and_registration(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert 'href="/support"' in html
        assert "Зарегистрироваться" in html
        assert "Подать заявку" not in html

    def test_feedback_block_for_user_links_to_account_feedback(self):
        app = _make_app(user=_user_mock(tester_status="approved"))
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        html = response.text
        assert "/support" in html
        assert "/account/feedback" in html

    def test_feedback_block_ignores_pending_tester_status(self):
        app = _make_app(user=_user_mock(tester_status="pending"))
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        html = response.text
        assert "заявка на рассмотрении" not in html.lower()
        assert "/account/feedback" in html

    def test_feedback_block_ignores_none_tester_status(self):
        app = _make_app(user=_user_mock(tester_status="none"))
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")
        html = response.text
        assert "/account/feedback" in html
        assert "Подать заявку" not in html
