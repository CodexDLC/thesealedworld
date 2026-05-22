from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from src.frontend.features.cabinet.modules.player_analytics import cabinet as player_analytics
from src.shared.schemas import GameLobbyPopulationStatsDTO


class _SessionContext:
    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.unit
async def test_registered_accounts_provider_counts_site_users(monkeypatch) -> None:
    class FakeUserRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        async def count_all(self) -> int:
            return 5

    monkeypatch.setattr(player_analytics, "get_session_context", lambda: _SessionContext(object()))
    monkeypatch.setattr(player_analytics, "UserRepository", FakeUserRepository)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    metric = await player_analytics._registered_accounts_provider(request)

    assert metric.key == "registered_accounts"
    assert metric.value == "5"
    assert metric.subtitle == "site.auth_users"


@pytest.mark.unit
async def test_characters_total_provider_reads_game_backend(monkeypatch) -> None:
    class FakeBackendGameLobbyApi:
        def __init__(self, *, client: object, base_url: str) -> None:
            self.client = client
            self.base_url = base_url

        async def get_population_stats(self) -> GameLobbyPopulationStatsDTO:
            return GameLobbyPopulationStatsDTO(characters_total=12)

    monkeypatch.setattr(player_analytics, "BackendGameLobbyApi", FakeBackendGameLobbyApi)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(backend_http_client=object())))

    metric = await player_analytics._characters_total_provider(request)

    assert metric.key == "characters_total"
    assert metric.value == "12"
    assert metric.subtitle == "game backend"


@pytest.mark.unit
async def test_characters_total_provider_marks_backend_unavailable(monkeypatch) -> None:
    class FakeBackendGameLobbyApi:
        def __init__(self, *, client: object, base_url: str) -> None:
            pass

        async def get_population_stats(self) -> GameLobbyPopulationStatsDTO:
            raise httpx.RequestError("offline")

    monkeypatch.setattr(player_analytics, "BackendGameLobbyApi", FakeBackendGameLobbyApi)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(backend_http_client=object())))

    metric = await player_analytics._characters_total_provider(request)

    assert metric.value == "—"
    assert metric.subtitle == "game backend недоступен"


@pytest.mark.unit
async def test_dau_today_provider_keeps_activity_separate_from_account_total(monkeypatch) -> None:
    class FakeDailyActivityRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        async def get_today_dau(self) -> int:
            return 2

    monkeypatch.setattr(player_analytics, "get_session_context", lambda: _SessionContext(object()))
    monkeypatch.setattr(player_analytics, "PlayerDailyActivityRepository", FakeDailyActivityRepository)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(player_presence={"u1": 1.0})))

    metric = await player_analytics._dau_today_provider(request)

    assert metric.key == "dau_today"
    assert metric.value == "2"
