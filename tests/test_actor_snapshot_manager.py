from __future__ import annotations

from typing import Any

import pytest

from src.backend.core.redis.actor_snapshot_manager import ActorSnapshotManager
from src.backend.features.actor_state.runtime.sections import resolve_sections

pytestmark = pytest.mark.unit


class FakeRedisService:
    def __init__(self, fail_set_keys: set[str] | None = None) -> None:
        self.redis_client = FakeRedisClient(fail_set_keys or set())


class FakeRedisClient:
    def __init__(self, fail_set_keys: set[str]) -> None:
        self.store: dict[str, dict[str, Any]] = {}
        self.ttls: dict[str, int] = {}
        self.fail_set_keys = fail_set_keys

    def pipeline(self, transaction: bool = False) -> FakePipeline:
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, client: FakeRedisClient) -> None:
        self.client = client
        self.commands: list[tuple[str, str, str | int | dict[str, Any] | None]] = []

    async def __aenter__(self) -> FakePipeline:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def json(self) -> FakePipeline:
        return self

    def set(self, key: str, path: str, value: dict[str, Any]) -> FakePipeline:
        self.commands.append(("json_set", key, value))
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
                    continue
                self.client.store[key] = payload  # type: ignore[assignment]
                results.append(True)
            elif command == "expire":
                if key not in self.client.store:
                    results.append(False)
                    continue
                self.client.ttls[key] = int(payload)
                results.append(True)
            elif command == "json_get":
                doc = self.client.store.get(key)
                if doc is None:
                    results.append(None)
                elif payload == "$":
                    results.append([doc])
                else:
                    section = str(payload).removeprefix("$.")
                    results.append([doc.get(section)])
        return results


@pytest.mark.asyncio
async def test_save_snapshots_round_trips_normalized_shape_and_ttl() -> None:
    redis = FakeRedisService()
    manager = ActorSnapshotManager(redis)  # type: ignore[arg-type]
    snapshots = {
        "combat-1:player:1": {"meta": {"actor_type": "player"}, "source": {"character_id": 1}},
        "combat-1:monster:m1": {"meta": {"actor_type": "monster"}, "combat": {"hp": 10}, "source": {}},
        "combat-1:monster:m2": {"meta": {"actor_type": "monster"}, "status": {"hp_current": -1}, "source": {}},
        "combat-1:monster:m3": {"meta": {"actor_type": "monster"}, "inventory": {}, "source": {}},
    }

    saved = await manager.save_snapshots(snapshots, ttl=123)

    assert len(saved) == 4
    assert redis.redis_client.ttls[saved["combat-1:player:1"]] == 123
    docs = await manager.get_snapshots_batch(list(saved.values()))
    player_doc = docs[saved["combat-1:player:1"]]
    assert player_doc == {
        "meta": {"actor_type": "player"},
        "runtime": {},
        "combat": {},
        "inventory": {},
        "status": {},
        "source": {"character_id": 1},
    }


@pytest.mark.asyncio
async def test_save_snapshots_omits_partial_pipeline_failures() -> None:
    failed_key = "game:actor:snapshot:combat-1:monster:m2"
    redis = FakeRedisService(fail_set_keys={failed_key})
    manager = ActorSnapshotManager(redis)  # type: ignore[arg-type]

    saved = await manager.save_snapshots(
        {
            "combat-1:player:1": {"meta": {"actor_type": "player"}, "source": {}},
            "combat-1:monster:m2": {"meta": {"actor_type": "monster"}, "source": {}},
        }
    )

    assert saved == {"combat-1:player:1": "game:actor:snapshot:combat-1:player:1"}


@pytest.mark.asyncio
async def test_get_sections_batch_fetches_requested_section() -> None:
    redis = FakeRedisService()
    manager = ActorSnapshotManager(redis)  # type: ignore[arg-type]
    saved = await manager.save_snapshots(
        {
            "sid:player:1": {"meta": {}, "combat": {"math_model": {"attributes": {}}}, "source": {}},
            "sid:monster:m1": {"meta": {}, "combat": {"math_model": {"tags": ["monster"]}}, "source": {}},
        }
    )

    sections = await manager.get_sections_batch(list(saved.values()), "combat")

    assert sections["game:actor:snapshot:sid:player:1"] == {"math_model": {"attributes": {}}}
    assert sections["game:actor:snapshot:sid:monster:m1"] == {"math_model": {"tags": ["monster"]}}


def test_resolve_sections_include_exclude_and_forced_meta_source() -> None:
    assert resolve_sections({"combat"}, set()) == {"combat", "meta", "source"}
    assert "inventory" not in resolve_sections(None, {"inventory"})
    assert resolve_sections(set(), {"meta", "source"}) == {"meta", "source"}
