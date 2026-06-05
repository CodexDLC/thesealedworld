from typing import Any

import pytest


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Any:
    from src.frontend import app as frontend_app_module
    from src.frontend.app import app

    async def _noop() -> None:
        return None

    async def _noop_rollup_loop(_app: Any) -> None:
        return None

    monkeypatch.setattr(frontend_app_module, "create_db_tables", _noop)
    monkeypatch.setattr(frontend_app_module, "close_db_engine", _noop)
    monkeypatch.setattr(frontend_app_module, "player_presence_rollup_loop", _noop_rollup_loop)

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: Any) -> Any:
    from fastapi.testclient import TestClient

    from src.frontend.config.settings import settings

    with TestClient(app) as c:
        # Bootstrap a CSRF cookie once; CsrfMiddleware will validate the same
        # token on every unsafe request, so we mirror it into the default header.
        c.get("/health")
        token = c.cookies.get(settings.csrf_cookie_name) or ""
        if token:
            c.headers[settings.csrf_header_name] = token
        yield c
