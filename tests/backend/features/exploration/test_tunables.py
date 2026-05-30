from __future__ import annotations

import pytest

from src.backend.features.exploration.game_config import ExplorationConfig
from src.backend.features.exploration.runtime.tunables import (
    DEFAULT_EXPLORATION_TUNABLES,
    ExplorationTunables,
    current_tunables,
    load_exploration_tunables,
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
def manager() -> GameConfigManager:
    mgr = GameConfigManager(FakeRedis())  # type: ignore[arg-type]
    mgr.register(ExplorationConfig)
    return mgr


class TestDefaults:
    def test_default_tunables_match_class_defaults(self) -> None:
        d = DEFAULT_EXPLORATION_TUNABLES
        assert d.chance_combat_base == ExplorationConfig.CHANCE_COMBAT_BASE
        assert d.chance_combat_search == ExplorationConfig.CHANCE_COMBAT_SEARCH
        assert d.encounter_session_ttl_seconds == ExplorationConfig.ENCOUNTER_SESSION_TTL_SECONDS
        assert d.default_spawn_point == ExplorationConfig.DEFAULT_SPAWN_POINT

    def test_dict_tables_kept_on_class(self) -> None:
        # Dicts stay on the class; only scalars are surfaced via tunables.
        assert isinstance(ExplorationConfig.TIER_DIFFICULTY_WEIGHTS, dict)
        assert isinstance(ExplorationConfig.DETECTION_MODIFIERS, dict)
        assert "easy" in ExplorationConfig.DETECTION_MODIFIERS


class TestLoader:
    async def test_load_with_none_returns_defaults(self) -> None:
        assert await load_exploration_tunables(None) == DEFAULT_EXPLORATION_TUNABLES

    async def test_load_picks_up_redis_overrides(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("exploration", "CHANCE_COMBAT_BASE", "0.10")
        await manager.set("exploration", "ENCOUNTER_SESSION_TTL_SECONDS", "60")

        tunables = await load_exploration_tunables(manager)

        assert tunables.chance_combat_base == 0.10
        assert tunables.encounter_session_ttl_seconds == 60
        # untouched key still default
        assert tunables.chance_combat_search == DEFAULT_EXPLORATION_TUNABLES.chance_combat_search

    async def test_load_tolerates_garbage_value(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("exploration", "CHANCE_COMBAT_BASE", "not-a-number")

        tunables = await load_exploration_tunables(manager)

        assert tunables.chance_combat_base == DEFAULT_EXPLORATION_TUNABLES.chance_combat_base


class TestContextVar:
    def test_current_tunables_returns_default_outside_context(self) -> None:
        assert current_tunables() == DEFAULT_EXPLORATION_TUNABLES

    def test_use_tunables_swaps_active_snapshot(self) -> None:
        override = ExplorationTunables(chance_combat_base=0.99)

        with use_tunables(override):
            assert current_tunables().chance_combat_base == 0.99

        assert current_tunables() == DEFAULT_EXPLORATION_TUNABLES

    def test_use_tunables_restores_after_exception(self) -> None:
        override = ExplorationTunables(chance_combat_base=0.99)

        with pytest.raises(RuntimeError):
            with use_tunables(override):
                raise RuntimeError("boom")

        assert current_tunables() == DEFAULT_EXPLORATION_TUNABLES
