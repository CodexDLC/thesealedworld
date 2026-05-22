from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.core.middleware import SiteAnalyticsMiddleware
from src.frontend.features.cabinet.modules.site_analytics import cabinet as site_analytics


class _SessionContext:
    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.unit
async def test_site_analytics_middleware_counts_current_lobby_route() -> None:
    request = _request_for_path("/game-lobby")
    middleware = SiteAnalyticsMiddleware(app=SimpleNamespace())

    await middleware.dispatch(request, _ok_response)

    assert request.app.state.site_analytics["visits"] == 1
    assert request.app.state.site_analytics["lobby_visits"] == 1
    assert "game_joins" not in request.app.state.site_analytics


@pytest.mark.unit
async def test_site_analytics_middleware_counts_current_game_enter_route() -> None:
    request = _request_for_path("/game-lobby/enter", method="POST")
    middleware = SiteAnalyticsMiddleware(app=SimpleNamespace())

    await middleware.dispatch(request, _ok_response)

    assert request.app.state.site_analytics["game_joins"] == 1
    assert "lobby_visits" not in request.app.state.site_analytics


@pytest.mark.unit
async def test_site_analytics_middleware_does_not_count_removed_legacy_event_paths() -> None:
    request = _request_for_path("/lobby")
    middleware = SiteAnalyticsMiddleware(app=SimpleNamespace())

    await middleware.dispatch(request, _ok_response)

    assert request.app.state.site_analytics["visits"] == 1
    assert "lobby_visits" not in request.app.state.site_analytics


@pytest.mark.unit
async def test_registrations_provider_counts_site_users(monkeypatch) -> None:
    class FakeUserRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        async def count_all(self) -> int:
            return 8

    monkeypatch.setattr(site_analytics, "get_session_context", lambda: _SessionContext(object()), raising=False)
    monkeypatch.setattr(site_analytics, "UserRepository", FakeUserRepository, raising=False)

    metric = await site_analytics._registrations_provider(_provider_request())

    assert metric.key == "registrations"
    assert metric.value == "8"
    assert metric.subtitle == "site.auth_users"


@pytest.mark.unit
async def test_active_combats_provider_counts_backend_sessions(monkeypatch) -> None:
    class FakeCombatSessionsApi:
        def __init__(self, *, client: object, base_url: str) -> None:
            self.client = client
            self.base_url = base_url

        async def list_active(self) -> list[dict]:
            return [{"session_id": "c1"}, {"session_id": "c2"}]

    monkeypatch.setattr(site_analytics, "CombatSessionsApi", FakeCombatSessionsApi, raising=False)

    metric = await site_analytics._active_combats_provider(_provider_request())

    assert metric.value == "2"
    assert metric.subtitle == "game backend"


@pytest.mark.unit
async def test_active_scenarios_provider_counts_backend_sessions(monkeypatch) -> None:
    class FakeScenarioSessionsApi:
        def __init__(self, *, client: object, base_url: str) -> None:
            self.client = client
            self.base_url = base_url

        async def list_active(self) -> list[dict]:
            return [{"session_id": "s1"}]

    monkeypatch.setattr(site_analytics, "ScenarioSessionsApi", FakeScenarioSessionsApi, raising=False)

    metric = await site_analytics._active_scenarios_provider(_provider_request())

    assert metric.value == "1"
    assert metric.subtitle == "game backend"


@pytest.mark.unit
async def test_active_travels_provider_reports_backend_unavailable(monkeypatch) -> None:
    class FakeExplorationSessionsApi:
        def __init__(self, *, client: object, base_url: str) -> None:
            pass

        async def list_active(self) -> list[dict]:
            raise httpx.RequestError("offline")

    monkeypatch.setattr(site_analytics, "ExplorationSessionsApi", FakeExplorationSessionsApi, raising=False)

    metric = await site_analytics._active_travels_provider(_provider_request())

    assert metric.value == "0"
    assert metric.subtitle == "game backend недоступен"


async def _ok_response(request: Request) -> Response:
    return Response("ok")


def _request_for_path(path: str, *, method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
            "app": SimpleNamespace(state=SimpleNamespace(site_analytics={})),
        }
    )


def _provider_request() -> SimpleNamespace:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(backend_http_client=object(), site_analytics={})))
