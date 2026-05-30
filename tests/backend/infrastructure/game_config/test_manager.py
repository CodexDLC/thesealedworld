from __future__ import annotations

import pytest

from src.backend.features.combat.game_config import CombatConfig
from src.backend.features.exploration.game_config import ExplorationConfig
from src.backend.features.scenario.game_config import ScenarioConfig
from src.backend.infrastructure.game_config.manager import GameConfigManager


class FakeRedis:
    """Minimal async stand-in for redis.asyncio.Redis with NX support."""

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
    mgr.register(ScenarioConfig)
    mgr.register(ExplorationConfig)
    return mgr


def _parry_key() -> str:
    return CombatConfig.redis_key("PARRY_SKILL_MULT_PER_POINT")


class TestBootstrap:
    async def test_writes_defaults_for_missing_keys(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        await manager.bootstrap()

        assert redis_client.store[_parry_key()] == str(CombatConfig.PARRY_SKILL_MULT_PER_POINT)
        for ns_cls in (CombatConfig, ScenarioConfig, ExplorationConfig):
            for key, default in ns_cls.defaults().items():
                assert redis_client.store[ns_cls.redis_key(key)] == str(default)

    async def test_preserves_existing_override_across_restart(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        redis_client.store[_parry_key()] = "9.5"

        await manager.bootstrap()

        assert redis_client.store[_parry_key()] == "9.5"

    async def test_second_bootstrap_is_idempotent(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        await manager.bootstrap()
        # Simulate an admin override.
        await manager.set("combat", "PARRY_SKILL_MULT_PER_POINT", "7.0")

        await manager.bootstrap()

        assert redis_client.store[_parry_key()] == "7.0"


class TestTypedGetters:
    async def test_get_float_returns_redis_value(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("combat", "PARRY_SKILL_MULT_PER_POINT", "7.25")

        assert await manager.get_float("combat", "PARRY_SKILL_MULT_PER_POINT") == 7.25

    async def test_get_float_falls_back_to_registered_default_on_garbage(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        await manager.bootstrap()
        redis_client.store[_parry_key()] = "not-a-number"

        result = await manager.get_float("combat", "PARRY_SKILL_MULT_PER_POINT", default=1.0)

        assert result == float(CombatConfig.PARRY_SKILL_MULT_PER_POINT)

    async def test_get_int_parses_int_value(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("combat", "CHAOS_FIRST_CHECK_DELAY_SECONDS", "120")

        assert await manager.get_int("combat", "CHAOS_FIRST_CHECK_DELAY_SECONDS") == 120

    async def test_get_int_tolerates_float_string(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("combat", "CHAOS_FIRST_CHECK_DELAY_SECONDS", "120.0")

        assert await manager.get_int("combat", "CHAOS_FIRST_CHECK_DELAY_SECONDS") == 120

    async def test_get_str_returns_registered_default_when_missing(
        self, manager: GameConfigManager
    ) -> None:
        # PARRY_SKILL_MULT_PER_POINT exists in config but no override in Redis yet (we skip bootstrap).
        result = await manager.get_str("combat", "PARRY_SKILL_MULT_PER_POINT")

        assert result == str(CombatConfig.PARRY_SKILL_MULT_PER_POINT)

    async def test_get_bool_parses_truthy_and_falsy(self, manager: GameConfigManager) -> None:
        # No bool field exists today; register a tiny ad-hoc namespace.
        from src.backend.infrastructure.game_config.base import BaseGameConfig

        class _BoolConfig(BaseGameConfig):
            namespace = "_test_bool"
            FEATURE_ON: bool = True

        manager.register(_BoolConfig)
        await manager.bootstrap()
        await manager.set("_test_bool", "FEATURE_ON", "no")
        assert await manager.get_bool("_test_bool", "FEATURE_ON") is False
        await manager.set("_test_bool", "FEATURE_ON", "YES")
        assert await manager.get_bool("_test_bool", "FEATURE_ON") is True
        await manager.set("_test_bool", "FEATURE_ON", "garbage")
        assert await manager.get_bool("_test_bool", "FEATURE_ON") is True  # registered default

    async def test_unknown_namespace_returns_caller_default(self, manager: GameConfigManager) -> None:
        assert await manager.get_float("nope", "WHATEVER", default=4.2) == 4.2
        assert await manager.get_int("nope", "WHATEVER", default=7) == 7
        assert await manager.get_bool("nope", "WHATEVER", default=False) is False
        assert await manager.get_str("nope", "WHATEVER", default="fallback") == "fallback"

    async def test_unknown_key_returns_caller_default(self, manager: GameConfigManager) -> None:
        assert await manager.get_float("combat", "NOT_A_KEY", default=1.1) == 1.1


class TestWriteAndReset:
    async def test_set_rejects_unknown_key(self, manager: GameConfigManager) -> None:
        assert await manager.set("combat", "NOT_A_KEY", "1.0") is False

    async def test_set_rejects_unknown_namespace(self, manager: GameConfigManager) -> None:
        assert await manager.set("nope", "PARRY_SKILL_MULT_PER_POINT", "1.0") is False

    async def test_reset_restores_registered_default(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        await manager.bootstrap()
        await manager.set("combat", "PARRY_SKILL_MULT_PER_POINT", "9.0")

        assert await manager.reset("combat", "PARRY_SKILL_MULT_PER_POINT") is True
        assert redis_client.store[_parry_key()] == str(CombatConfig.PARRY_SKILL_MULT_PER_POINT)

    async def test_reset_rejects_unknown_namespace(self, manager: GameConfigManager) -> None:
        assert await manager.reset("nope", "anything") is False

    async def test_reset_namespace_restores_all_keys(
        self, manager: GameConfigManager, redis_client: FakeRedis
    ) -> None:
        await manager.bootstrap()
        await manager.set("combat", "PARRY_SKILL_MULT_PER_POINT", "9.0")
        await manager.set("combat", "SHIELD_BLOCK_SKILL_BONUS_AT_FULL", "0.9")

        assert await manager.reset_namespace("combat") is True

        for key, default in CombatConfig.defaults().items():
            assert redis_client.store[CombatConfig.redis_key(key)] == str(default)

    async def test_reset_namespace_rejects_unknown(self, manager: GameConfigManager) -> None:
        assert await manager.reset_namespace("nope") is False


class TestListing:
    async def test_list_namespace_returns_typed_entries(self, manager: GameConfigManager) -> None:
        await manager.bootstrap()
        await manager.set("combat", "PARRY_SKILL_MULT_PER_POINT", "7.0")

        entries = await manager.list_namespace("combat")
        entry_map = {e.key: e for e in entries}

        parry = entry_map["PARRY_SKILL_MULT_PER_POINT"]
        assert parry.current == "7.0"
        assert parry.default == str(CombatConfig.PARRY_SKILL_MULT_PER_POINT)
        assert parry.value_type == "float"
        assert parry.namespace == "combat"

        chaos = entry_map["CHAOS_FIRST_CHECK_DELAY_SECONDS"]
        assert chaos.value_type == "int"

    async def test_list_namespace_unknown_returns_empty(self, manager: GameConfigManager) -> None:
        assert await manager.list_namespace("nope") == []

    async def test_namespaces_returns_registered_names(self, manager: GameConfigManager) -> None:
        assert set(manager.namespaces()) == {"combat", "scenario", "exploration"}
