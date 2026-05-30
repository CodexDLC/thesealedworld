from __future__ import annotations

import pytest

from src.backend.features.rift.game_config import RiftConfig
from src.backend.features.rift.runtime.tunables import (
    DEFAULT_RIFT_TUNABLES,
    RiftTunables,
    current_tunables,
    load_rift_tunables,
    use_tunables,
)
from src.backend.infrastructure.game_config.manager import GameConfigManager


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, *, nx: bool = False, **_: object) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = str(value)
        return True


@pytest.fixture()
def redis_client() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def manager(redis_client: FakeRedis) -> GameConfigManager:
    mgr = GameConfigManager(redis_client)  # type: ignore[arg-type]
    mgr.register(RiftConfig)
    return mgr


class TestDefaults:
    def test_default_tunables_match_removed_master_runtime_values(self) -> None:
        d = DEFAULT_RIFT_TUNABLES
        assert d.transition_base_chance_per_tick == 0.35
        assert d.transition_tick_interval_ms == 1000
        assert d.transition_exploration_duration_ms == 3000
        assert d.transition_return_duration_ms == 1000
        assert d.transition_suppress_ordinary_after_combat is True
        assert d.ordinary_node_combat_enabled is True
        assert d.ordinary_node_first_visit_only is True
        assert d.ordinary_node_combat_chance == 0.3


class TestLoader:
    async def test_load_with_none_returns_defaults(self) -> None:
        assert await load_rift_tunables(None) == DEFAULT_RIFT_TUNABLES

    async def test_load_picks_up_redis_overrides(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("rift", "TRANSITION_BASE_CHANCE_PER_TICK", "0.9")
        await manager.set("rift", "ORDINARY_NODE_COMBAT_CHANCE", "0.0")
        await manager.set("rift", "TRANSITION_EXPLORATION_DURATION_MS", "5000")

        tunables = await load_rift_tunables(manager)

        assert tunables.transition_base_chance_per_tick == 0.9
        assert tunables.ordinary_node_combat_chance == 0.0
        assert tunables.transition_exploration_duration_ms == 5000
        assert tunables.transition_tick_interval_ms == DEFAULT_RIFT_TUNABLES.transition_tick_interval_ms


class TestContextVar:
    def test_current_tunables_returns_default_outside_context(self) -> None:
        assert current_tunables() == DEFAULT_RIFT_TUNABLES

    def test_use_tunables_swaps_active_snapshot(self) -> None:
        override = RiftTunables(transition_base_chance_per_tick=0.0)

        with use_tunables(override):
            assert current_tunables().transition_base_chance_per_tick == 0.0

        assert current_tunables() == DEFAULT_RIFT_TUNABLES
