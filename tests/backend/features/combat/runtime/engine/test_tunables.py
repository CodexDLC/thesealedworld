from __future__ import annotations

import pytest

from src.backend.features.combat.game_config import CombatConfig
from src.backend.features.combat.runtime.engine.tunables import (
    DEFAULT_COMBAT_TUNABLES,
    CombatTunables,
    current_tunables,
    load_combat_tunables,
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
    mgr.register(CombatConfig)
    return mgr


class TestDefaults:
    def test_default_tunables_match_legacy_constants(self) -> None:
        d = DEFAULT_COMBAT_TUNABLES
        assert d.parry_skill_mult_per_point == 4.0
        assert d.shield_block_skill_bonus_at_full == 0.32
        assert d.shield_mastery_absorb_cap_ratio_at_full == 0.50
        assert d.shield_mastery_reflect_ratio_at_full == 1.00
        assert d.base_accuracy_chance == 0.70
        assert d.skill_accuracy_bonus_at_full == 0.30
        assert d.accuracy_chance_cap == 0.90
        assert d.unarmed_min_efficiency == 0.5
        assert d.unarmed_max_efficiency == 3.0
        assert d.unarmed_novice_spread == 0.5
        assert d.unarmed_master_spread == 0.1
        assert d.token_bonus_chance == 0.30


class TestLoader:
    async def test_load_with_none_returns_defaults(self) -> None:
        assert await load_combat_tunables(None) == DEFAULT_COMBAT_TUNABLES

    async def test_load_picks_up_redis_overrides(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("combat", "PARRY_SKILL_MULT_PER_POINT", "9.5")
        await manager.set("combat", "BASE_ACCURACY_CHANCE", "0.5")
        await manager.set("combat", "ACCURACY_CHANCE_CAP", "0.95")

        tunables = await load_combat_tunables(manager)

        assert tunables.parry_skill_mult_per_point == 9.5
        assert tunables.base_accuracy_chance == 0.5
        assert tunables.accuracy_chance_cap == 0.95
        # untouched key falls back to default
        assert tunables.token_bonus_chance == DEFAULT_COMBAT_TUNABLES.token_bonus_chance

    async def test_load_tolerates_garbage_value(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        await manager.bootstrap()
        redis_client.store[CombatConfig.redis_key("PARRY_SKILL_MULT_PER_POINT")] = "not-a-number"

        tunables = await load_combat_tunables(manager)

        assert tunables.parry_skill_mult_per_point == DEFAULT_COMBAT_TUNABLES.parry_skill_mult_per_point


class TestContextVar:
    def test_current_tunables_returns_default_outside_context(self) -> None:
        assert current_tunables() == DEFAULT_COMBAT_TUNABLES

    def test_use_tunables_swaps_active_snapshot(self) -> None:
        override = CombatTunables(parry_skill_mult_per_point=99.0)

        with use_tunables(override):
            assert current_tunables().parry_skill_mult_per_point == 99.0

        assert current_tunables() == DEFAULT_COMBAT_TUNABLES

    def test_use_tunables_restores_after_exception(self) -> None:
        override = CombatTunables(parry_skill_mult_per_point=42.0)

        with pytest.raises(RuntimeError), use_tunables(override):
            raise RuntimeError("boom")

        assert current_tunables() == DEFAULT_COMBAT_TUNABLES
