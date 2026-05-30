from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.features.combat.api.internal_router import router as combat_internal_router
from src.backend.features.exploration.api.internal_router import router as exploration_internal_router
from src.backend.features.game_config.api.router import router as game_config_router
from src.backend.features.scenario.api.internal_router import router as scenario_internal_router


def _make_app(*routers) -> FastAPI:
    app = FastAPI()
    for r in routers:
        app.include_router(r)
    return app


# ── GameConfig router ────────────────────────────────────────────────────────


class FakeConfigManager:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, str]] = {
            "combat": {"round_time": "30"},
        }
        self._defaults: dict[str, dict[str, str]] = {
            "combat": {"round_time": "45"},
        }

    def namespaces(self) -> list[str]:
        return list(self._data)

    async def list_all(self) -> dict[str, list]:
        result = {}
        for ns in self._data:
            result[ns] = await self.list_namespace(ns)
        return result

    async def list_namespace(self, namespace: str) -> list:
        from src.backend.infrastructure.game_config.manager import ConfigEntry

        if namespace not in self._data:
            return []
        entries = []
        for key, current in self._data[namespace].items():
            default = self._defaults.get(namespace, {}).get(key, current)
            entries.append(
                ConfigEntry(
                    key=key,
                    namespace=namespace,
                    current=current,
                    default=default,
                    value_type="str",
                    label="Round time",
                    description="How long a round remains open.",
                    group="Timing",
                    unit="seconds",
                    min_value=1.0,
                    max_value=300.0,
                    step=1.0,
                    risk="medium",
                    live_scope="new_round",
                    tags=("combat", "timing"),
                )
            )
        return entries

    async def set(self, namespace: str, key: str, value: str) -> bool:
        if namespace not in self._data or key not in self._data[namespace]:
            return False
        if value == "invalid":
            from src.backend.infrastructure.game_config.manager import ConfigValidationError

            raise ConfigValidationError("round_time must be an int")
        self._data[namespace][key] = value
        return True

    async def reset(self, namespace: str, key: str) -> bool:
        if namespace not in self._defaults or key not in self._defaults.get(namespace, {}):
            return False
        self._data[namespace][key] = self._defaults[namespace][key]
        return True

    async def reset_namespace(self, namespace: str) -> bool:
        if namespace not in self._defaults:
            return False
        for key, default in self._defaults[namespace].items():
            self._data[namespace][key] = default
        return True


@pytest.fixture()
def config_client() -> TestClient:
    app = _make_app(game_config_router)
    app.state.game_config = FakeConfigManager()
    return TestClient(app)


class TestGameConfigRouter:
    def test_list_all(self, config_client: TestClient) -> None:
        resp = config_client.get("/api/internal/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "combat" in data
        assert len(data["combat"]) == 1
        assert data["combat"][0]["key"] == "round_time"

    def test_list_namespace(self, config_client: TestClient) -> None:
        resp = config_client.get("/api/internal/config/combat")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 1
        assert entries[0]["current"] == "30"
        assert entries[0]["default"] == "45"
        assert entries[0]["is_modified"] is True
        assert entries[0]["label"] == "Round time"
        assert entries[0]["group"] == "Timing"
        assert entries[0]["unit"] == "seconds"
        assert entries[0]["min_value"] == 1.0
        assert entries[0]["max_value"] == 300.0
        assert entries[0]["step"] == 1.0
        assert entries[0]["risk"] == "medium"
        assert entries[0]["live_scope"] == "new_round"
        assert entries[0]["tags"] == ["combat", "timing"]

    def test_list_namespace_unknown(self, config_client: TestClient) -> None:
        resp = config_client.get("/api/internal/config/nonexistent")
        assert resp.status_code == 404

    def test_set_value(self, config_client: TestClient) -> None:
        resp = config_client.patch("/api/internal/config/combat/round_time", json={"value": "60"})
        assert resp.status_code == 200
        assert resp.json()["value"] == "60"

    def test_set_value_unknown_key(self, config_client: TestClient) -> None:
        resp = config_client.patch("/api/internal/config/combat/unknown_key", json={"value": "1"})
        assert resp.status_code == 404

    def test_set_value_invalid_returns_422(self, config_client: TestClient) -> None:
        resp = config_client.patch("/api/internal/config/combat/round_time", json={"value": "invalid"})
        assert resp.status_code == 422
        assert "must be an int" in resp.json()["detail"]

    def test_reset_key(self, config_client: TestClient) -> None:
        config_client.patch("/api/internal/config/combat/round_time", json={"value": "99"})
        resp = config_client.delete("/api/internal/config/combat/round_time")
        assert resp.status_code == 200
        assert resp.json()["reset"] is True

    def test_reset_key_unknown(self, config_client: TestClient) -> None:
        resp = config_client.delete("/api/internal/config/combat/nope")
        assert resp.status_code == 404

    def test_reset_namespace(self, config_client: TestClient) -> None:
        resp = config_client.delete("/api/internal/config/combat")
        assert resp.status_code == 200
        assert resp.json()["reset"] is True

    def test_reset_namespace_unknown(self, config_client: TestClient) -> None:
        resp = config_client.delete("/api/internal/config/missing")
        assert resp.status_code == 404


# ── Combat internal router ───────────────────────────────────────────────────


@pytest.fixture()
def combat_client() -> TestClient:
    app = _make_app(combat_internal_router)

    mock_redis = MagicMock()
    mock_client = AsyncMock()

    mock_client.scan = AsyncMock(
        return_value=(0, [b"combat:rbc:abc-123:meta"]),
    )
    mock_client.hgetall = AsyncMock(
        return_value={
            b"active": b"1",
            b"status": b"active",
            b"battle_type": b"pve",
            b"step_counter": b"3",
            b"active_actors_count": b"2",
            b"winner": b"",
            b"started_at": b"1716100000",
            b"last_activity_at": b"1716100100",
        },
    )
    mock_redis.redis_client = mock_client
    app.state.redis = mock_redis
    return TestClient(app)


class TestCombatInternalRouter:
    def test_list_sessions(self, combat_client: TestClient) -> None:
        resp = combat_client.get("/api/internal/combat/sessions")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "abc-123"
        assert sessions[0]["status"] == "active"
        assert sessions[0]["battle_type"] == "pve"

    def test_get_session(self, combat_client: TestClient) -> None:
        resp = combat_client.get("/api/internal/combat/sessions/abc-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "abc-123"
        assert data["status"] == "active"

    def test_get_session_not_found(self, combat_client: TestClient) -> None:
        app = _make_app(combat_internal_router)
        mock_redis = MagicMock()
        mock_client = AsyncMock()
        mock_client.hgetall = AsyncMock(return_value={})
        mock_redis.redis_client = mock_client
        app.state.redis = mock_redis
        client = TestClient(app)
        resp = client.get("/api/internal/combat/sessions/nonexistent")
        assert resp.status_code == 404


# ── Exploration internal router ──────────────────────────────────────────────


@pytest.fixture()
def exploration_client() -> TestClient:
    app = _make_app(exploration_internal_router)

    mock_redis = MagicMock()
    mock_client = AsyncMock()
    mock_client.scan = AsyncMock(return_value=(0, ["game:encounter:enc-1"]))

    mock_json = AsyncMock()
    mock_json.get = AsyncMock(
        return_value=[
            {
                "encounter_id": "enc-1",
                "char_id": 42,
                "status": "active",
                "payload": {"type": "monster", "title": "Goblin Ambush"},
            }
        ],
    )

    mock_redis.redis_client = mock_client
    mock_redis.json_module = mock_json
    app.state.redis = mock_redis
    return TestClient(app)


class TestExplorationInternalRouter:
    def test_list_sessions(self, exploration_client: TestClient) -> None:
        resp = exploration_client.get("/api/internal/exploration/sessions")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["encounter_id"] == "enc-1"
        assert sessions[0]["char_id"] == "42"
        assert sessions[0]["type"] == "monster"
        assert sessions[0]["title"] == "Goblin Ambush"

    def test_list_sessions_empty(self) -> None:
        app = _make_app(exploration_internal_router)
        mock_redis = MagicMock()
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_redis.redis_client = mock_client
        app.state.redis = mock_redis
        client = TestClient(app)
        resp = client.get("/api/internal/exploration/sessions")
        assert resp.status_code == 200
        assert resp.json() == []


# ── Scenario internal router ─────────────────────────────────────────────────


@pytest.fixture()
def scenario_client() -> TestClient:
    app = _make_app(scenario_internal_router)

    mock_redis = MagicMock()
    mock_client = AsyncMock()
    mock_client.scan = AsyncMock(return_value=(0, ["game:ac:7:scenario"]))

    mock_json = AsyncMock()
    mock_json.get = AsyncMock(
        return_value=[
            {
                "scenario_session_id": "scn-001",
                "quest_key": "tutorial_intro",
                "current_node_key": "node_3",
                "step_counter": 3,
                "total_steps": 10,
                "updated_at": "2025-05-18T12:00:00",
            }
        ],
    )

    mock_redis.redis_client = mock_client
    mock_redis.json_module = mock_json
    app.state.redis = mock_redis
    return TestClient(app)


class TestScenarioInternalRouter:
    def test_list_sessions(self, scenario_client: TestClient) -> None:
        resp = scenario_client.get("/api/internal/scenario/sessions")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["char_id"] == "7"
        assert sessions[0]["session_id"] == "scn-001"
        assert sessions[0]["quest_key"] == "tutorial_intro"
        assert sessions[0]["step"] == "3/10"

    def test_list_sessions_empty(self) -> None:
        app = _make_app(scenario_internal_router)
        mock_redis = MagicMock()
        mock_client = AsyncMock()
        mock_client.scan = AsyncMock(return_value=(0, []))
        mock_redis.redis_client = mock_client
        app.state.redis = mock_redis
        client = TestClient(app)
        resp = client.get("/api/internal/scenario/sessions")
        assert resp.status_code == 200
        assert resp.json() == []
