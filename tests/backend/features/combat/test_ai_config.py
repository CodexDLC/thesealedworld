from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.backend.features.combat.ai_config import CombatAiConfig
from src.backend.features.combat.runtime.ai.policy import Policy
from src.backend.features.combat.runtime.ai.policy_store import PolicyStore
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


class TestCombatAiConfigNamespace:
    def test_registered_fields_are_scalars(self) -> None:
        defaults = CombatAiConfig.defaults()
        assert defaults["ACTIVE_POLICY_ID"] == ""
        assert defaults["EXPLORATION_RANDOMNESS_MULT"] == 1.0
        assert defaults["TRAINING_ENABLED"] is False
        assert defaults["TRAINING_SEED"] == 0

    def test_namespace_is_distinct_from_combat(self) -> None:
        assert CombatAiConfig.namespace == "combat_ai"

    async def test_manager_exposes_typed_reads(self) -> None:
        mgr = GameConfigManager(FakeRedis())  # type: ignore[arg-type]
        mgr.register(CombatAiConfig)
        await mgr.bootstrap()

        await mgr.set("combat_ai", "ACTIVE_POLICY_ID", "trained_g500_seed0")
        await mgr.set("combat_ai", "TRAINING_ENABLED", "true")
        await mgr.set("combat_ai", "EXPLORATION_RANDOMNESS_MULT", "0.25")

        assert await mgr.get_str("combat_ai", "ACTIVE_POLICY_ID") == "trained_g500_seed0"
        assert await mgr.get_bool("combat_ai", "TRAINING_ENABLED") is True
        assert await mgr.get_float("combat_ai", "EXPLORATION_RANDOMNESS_MULT") == 0.25


class TestPolicyStorePolicyIdResolution:
    def test_load_with_policy_id_picks_named_artifact(self, tmp_path: Path) -> None:
        # Write a synthetic policy file into the real bundled policies/ dir under a
        # safe namespaced id; this exercises the resolved-path branch.
        policies_dir = Path(__import__("src.backend.features.combat.runtime.ai.policy_store", fromlist=[""]).__file__).resolve().parent / "policies"
        marker_id = "_pytest_phase6_marker"
        marker_path = policies_dir / f"{marker_id}.json"
        marker_path.write_text(
            json.dumps(
                {
                    "policy_id": marker_id,
                    "version": 1,
                    "weights": {"randomness": 0.42},
                    "metadata": {"phase": "p6"},
                }
            ),
            encoding="utf-8",
        )
        try:
            store = PolicyStore()
            policy = store.load(policy_id=marker_id)

            assert policy.policy_id == marker_id
            assert policy.weights.get("randomness") == 0.42
        finally:
            marker_path.unlink(missing_ok=True)

    def test_load_with_unknown_policy_id_falls_back_to_default(self) -> None:
        store = PolicyStore()

        policy = store.load(policy_id="this-id-does-not-exist-anywhere-xyz")

        # Falls back to bundled default — verified by the presence of a
        # known stable weight key (default policy is filled via with_defaults).
        assert isinstance(policy.weights, dict)
        assert "randomness" in policy.weights

    def test_load_with_empty_policy_id_uses_env_or_default(self) -> None:
        store = PolicyStore()

        policy = store.load(policy_id="")

        assert isinstance(policy.weights, dict)
        assert "randomness" in policy.weights


class TestBattleMetaAiPolicyId:
    def test_battle_meta_accepts_policy_id_field(self) -> None:
        from src.backend.features.combat.dto.session import BattleMeta

        meta = BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=2,
            teams={"team_1": [1], "team_2": [2]},
            battle_type="pve",
            location_id="arena",
            ai_policy_id="trained_g500_seed0",
        )

        assert meta.ai_policy_id == "trained_g500_seed0"

    def test_battle_meta_defaults_policy_id_to_empty_string(self) -> None:
        from src.backend.features.combat.dto.session import BattleMeta

        meta = BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=2,
            teams={"team_1": [1], "team_2": [2]},
            battle_type="pve",
            location_id="arena",
        )

        assert meta.ai_policy_id == ""


class TestAiTurnPolicyResolver:
    async def test_loads_active_policy_from_training_run_metadata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import importlib
        from types import SimpleNamespace

        ai_turn_task_module = importlib.import_module("src.backend.features.combat.workers.tasks.ai_turn_task")

        policy = Policy.with_defaults(policy_id="db-training-policy", weights={"team_focus": 1.0})
        training_row = SimpleNamespace(
            id="training-1",
            run_kind="training",
            status="completed",
            reward=21.8,
            metadata_={"best_policy": policy.model_dump(mode="json")},
        )

        class FakeSessionContext:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class FakeRepository:
            def __init__(self, _session) -> None:
                pass

            async def get(self, run_id: str):
                assert run_id == "training-1"
                return training_row

        monkeypatch.setattr(ai_turn_task_module, "get_session_context", lambda: FakeSessionContext())
        monkeypatch.setattr(ai_turn_task_module, "CombatAiSimulationRunRepository", FakeRepository)

        ctx: dict[str, object] = {}
        default_processor = object()
        processor = await ai_turn_task_module._ai_processor_for_policy(ctx, "training-1", default_processor)

        assert processor is not default_processor
        assert processor._brain.policy.policy_id == "db-training-policy"  # noqa: SLF001
        assert ctx["ai_policy_processor_cache"]["training-1"] is processor  # type: ignore[index]


class TestLifecycleSnapshotsAiPolicyId:
    async def test_lifecycle_resolves_active_policy_via_game_config(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService

        store = MagicMock()
        store.create_session_batch = AsyncMock()
        store.append_analytics = AsyncMock()
        game_config = MagicMock()
        game_config.get_int = AsyncMock(return_value=3600)
        game_config.get_str = AsyncMock(return_value="trained_g500_seed0")

        svc = CombatLifecycleService(store=store, game_config=game_config)

        snapshots = {
            "player:1": {
                "meta": {"name": "Alice"},
                "combat": {},
                "status": {"hp": 100, "max_hp": 100},
            },
            "player:2": {
                "meta": {"name": "Bob"},
                "combat": {},
                "status": {"hp": 100, "max_hp": 100},
            },
        }
        await svc.create_session_from_snapshots(
            "combat-1",
            battle_type="pve",
            participants={"team_1": [1], "team_2": [2]},
            snapshots=snapshots,
            request={"loc_id": "arena_test"},
        )

        # game_config.get_str was asked specifically for ACTIVE_POLICY_ID with
        # the combat_ai namespace, default empty.
        game_config.get_str.assert_awaited_once_with(
            "combat_ai", "ACTIVE_POLICY_ID", default=""
        )

        # The resolved id ends up in the meta hash passed to create_session_batch.
        store.create_session_batch.assert_awaited_once()
        _, kwargs = store.create_session_batch.call_args
        session_data = store.create_session_batch.call_args.args[1]
        assert session_data.meta["ai_policy_id"] == "trained_g500_seed0"

    async def test_lifecycle_without_game_config_writes_empty_policy_id(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService

        store = MagicMock()
        store.create_session_batch = AsyncMock()
        store.append_analytics = AsyncMock()

        svc = CombatLifecycleService(store=store, game_config=None)

        snapshots = {
            "player:1": {"meta": {}, "combat": {}, "status": {"hp": 1, "max_hp": 1}},
            "player:2": {"meta": {}, "combat": {}, "status": {"hp": 1, "max_hp": 1}},
        }
        await svc.create_session_from_snapshots(
            "combat-2",
            battle_type="pve",
            participants={"team_1": [1], "team_2": [2]},
            snapshots=snapshots,
            request={},
        )

        session_data = store.create_session_batch.call_args.args[1]
        assert session_data.meta["ai_policy_id"] == ""


class TestSessionIntegrationParsesPolicyId:
    def test_parse_meta_picks_up_policy_id(self) -> None:
        from src.backend.features.combat.integrations.session_integration import (
            CombatSessionIntegration,
        )

        integration = object.__new__(CombatSessionIntegration)
        raw = {
            "active": "1",
            "step_counter": "0",
            "teams": '{"team_1": [1], "team_2": [2]}',
            "actors_info": "{}",
            "dead_actors": "[]",
            "last_activity_at": "0",
            "battle_type": "pve",
            "location_id": "arena",
            "ai_policy_id": "trained_g500_seed0",
        }

        meta = CombatSessionIntegration._parse_meta(integration, raw)

        assert meta.ai_policy_id == "trained_g500_seed0"

    def test_parse_meta_defaults_missing_policy_id_to_empty(self) -> None:
        from src.backend.features.combat.integrations.session_integration import (
            CombatSessionIntegration,
        )

        integration = object.__new__(CombatSessionIntegration)
        raw = {
            "active": "1",
            "step_counter": "0",
            "teams": "{}",
            "battle_type": "pve",
            "location_id": "arena",
        }

        meta = CombatSessionIntegration._parse_meta(integration, raw)

        assert meta.ai_policy_id == ""
