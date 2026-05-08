from __future__ import annotations

from typing import Any

import pytest


class FakeRedisClient:
    def __init__(self, fail_set_keys: set[str] | None = None) -> None:
        self.store: dict[str, dict[str, Any]] = {}
        self.ttls: dict[str, int] = {}
        self.fail_set_keys = fail_set_keys or set()

    def pipeline(self, transaction: bool = False) -> FakePipeline:
        return FakePipeline(self)

    async def set(self, key: str, path: str, value: Any) -> bool:
        if key in self.fail_set_keys:
            return False
        if path == "$":
            self.store[key] = value
        elif path.startswith("$."):
            if key not in self.store:
                self.store[key] = {}
            self._set_path(self.store[key], path.removeprefix("$."), value)
        return True

    async def get(self, key: str, path: str = "$") -> list[Any] | None:
        doc = self.store.get(key)
        if doc is None:
            return None
        if path == "$":
            return [doc]
        return [self._get_path(doc, str(path).removeprefix("$."))]

    async def expire(self, key: str, ttl: int) -> bool:
        if key not in self.store:
            return False
        self.ttls[key] = ttl
        return True

    async def delete(self, key: str) -> bool:
        if key in self.store:
            del self.store[key]
            if key in self.ttls:
                del self.ttls[key]
            return True
        return False

    async def scan(self, cursor: int = 0, match: str | None = None, count: int = 100) -> tuple[int, list[str]]:
        prefix = (match or "").removesuffix("*")
        keys = [key for key in self.store if not prefix or key.startswith(prefix)]
        return 0, keys[:count]

    @staticmethod
    def _set_path(doc: dict[str, Any], dotted: str, value: Any) -> None:
        current = doc
        parts = dotted.split(".")
        for part in parts[:-1]:
            next_value = current.get(part)
            if not isinstance(next_value, dict):
                next_value = {}
                current[part] = next_value
            current = next_value
        current[parts[-1]] = value

    @staticmethod
    def _get_path(doc: dict[str, Any], dotted: str) -> Any:
        current: Any = doc
        for part in dotted.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

class FakePipeline:
    def __init__(self, client: FakeRedisClient) -> None:
        self.client = client
        self.commands: list[tuple[str, str, Any]] = []

    async def __aenter__(self) -> FakePipeline:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def json(self) -> FakePipeline:
        return self

    def set(self, key: str, path: str, value: dict[str, Any]) -> FakePipeline:
        self.commands.append(("json_set", key, (path, value)))
        return self

    def get(self, key: str, path: str = "$") -> FakePipeline:
        self.commands.append(("json_get", key, path))
        return self

    def expire(self, key: str, ttl: int) -> FakePipeline:
        self.commands.append(("expire", key, ttl))
        return self

    async def execute(self, raise_on_error: bool = True) -> list[Any]:
        results: list[Any] = []
        for command, key, payload in self.commands:
            if command == "json_set":
                if key in self.client.fail_set_keys:
                    results.append(RuntimeError("write failed"))
                else:
                    path, value = payload
                    if path == "$":
                        self.client.store[key] = value
                    elif str(path).startswith("$."):
                        if key not in self.client.store or not isinstance(self.client.store[key], dict):
                            self.client.store[key] = {}
                        self.client._set_path(self.client.store[key], str(path).removeprefix("$."), value)
                    results.append(True)
            elif command == "expire":
                if key not in self.client.store:
                    results.append(False)
                else:
                    self.client.ttls[key] = int(payload)
                    results.append(True)
            elif command == "json_get":
                doc = self.client.store.get(key)
                if doc is None:
                    results.append(None)
                elif payload == "$":
                    results.append([doc])
                else:
                    results.append([self.client._get_path(doc, str(payload).removeprefix("$."))])
        return results

class FakeRedisService:
    def __init__(self, client: FakeRedisClient) -> None:
        self.redis_client = client
        self.json_module = client
        self.string = client

@pytest.fixture
def fake_redis_client() -> FakeRedisClient:
    return FakeRedisClient()

@pytest.fixture
def fake_redis_service(fake_redis_client: FakeRedisClient) -> FakeRedisService:
    return FakeRedisService(fake_redis_client)


@pytest.fixture
def app() -> Any:
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.backend.app import app

    # Mock app state and lifespan components to avoid real connections
    app.state.redis_client = AsyncMock()
    app.state.redis_client.close = AsyncMock()
    app.state.events = MagicMock()
    app.state.redis = MagicMock()
    app.state.redis_managers = MagicMock()
    app.state.character_sessions = MagicMock()
    app.state.actor_commitments = MagicMock()
    app.state.scenario_sessions = MagicMock()
    app.state.world_locations = MagicMock()

    # Globally mock lifespan containers for this app instance to avoid side effects.
    with patch("src.backend.core.lifespan.DatabaseContainer.bootstrap", new_callable=AsyncMock), \
         patch("src.backend.core.lifespan.RedisContainer.bootstrap", new_callable=AsyncMock), \
         patch("src.backend.core.lifespan.AIContainer.bootstrap", new_callable=AsyncMock), \
         patch("src.backend.core.lifespan.GameFeatureContainer.bootstrap", new_callable=AsyncMock):
        yield app


@pytest.fixture
def client(app: Any) -> Any:
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
