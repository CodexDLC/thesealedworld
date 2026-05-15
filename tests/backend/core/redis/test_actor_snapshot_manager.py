from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from src.backend.infrastructure.actor_commitments import ActorCommitmentManager
from src.backend.infrastructure.actor_commitments.manager import resolve_sections


@pytest.mark.unit
class TestActorCommitmentManager:
    @pytest.fixture
    def manager(self, fake_redis_service):
        return ActorCommitmentManager(fake_redis_service)

    async def test_save_commitments_round_trips_normalized_shape_and_ttl(self, manager, fake_redis_client):
        snapshots = {
            "actor-player-1": {"meta": {"actor_type": "player"}, "source": {"character_id": 1}},
            "actor-monster-m1": {"meta": {"actor_type": "monster"}, "combat": {"hp": 10}, "source": {}},
        }

        saved = await manager.save_snapshots(snapshots, ttl=123)

        assert len(saved) == 2
        assert fake_redis_client.ttls["game:combat:snapshot:actor-player-1"] == 123

        docs = await manager.get_snapshots_batch(list(saved.values()))
        player_doc = docs[saved["actor-player-1"]]
        assert player_doc["actor_id"] == "actor-player-1"
        assert player_doc["meta"] == {"actor_type": "player"}
        assert player_doc["source"] == {"character_id": 1}
        assert player_doc["combat"] is None
        assert player_doc["inventory"] is None

    async def test_save_commitments_omits_partial_pipeline_failures(self, manager, fake_redis_client):
        # We need to know the actual key to fail it.
        # Since it's flat now, it's game:combat:snapshot:actor-monster-m2
        failed_key = "game:combat:snapshot:actor-monster-m2"
        fake_redis_client.fail_set_keys.add(failed_key)

        saved = await manager.save_snapshots(
            {
                "actor-player-1": {"meta": {"actor_type": "player"}, "source": {}},
                "actor-monster-m2": {"meta": {"actor_type": "monster"}, "source": {}},
            },
        )

        assert saved == {"actor-player-1": "actor-player-1"}

    async def test_get_sections_batch_fetches_requested_section(self, manager, fake_redis_client):
        # Manually seed fake store
        fake_redis_client.store["game:combat:snapshot:p1"] = {"meta": {}, "combat": {"hp": 100}, "source": {}}
        fake_redis_client.store["game:combat:snapshot:m1"] = {"meta": {}, "combat": {"hp": 50}, "source": {}}

        sections = await manager.get_sections_batch(["p1", "m1"], "combat")

        assert sections["p1"] == {"hp": 100}
        assert sections["m1"] == {"hp": 50}

    async def test_save_commitment_individual_operation(self, manager, fake_redis_client):
        actor_id = "actor-player-1"
        data = {"meta": {"actor_type": "player"}, "status": {"hp": 100}}

        key = await manager.save_snapshot(actor_id, data, ttl=3600)

        assert key == actor_id
        redis_key = "game:combat:snapshot:actor-player-1"
        assert fake_redis_client.store[redis_key]["status"] == {"hp": 100}
        assert fake_redis_client.store[redis_key]["combat"] is None
        assert fake_redis_client.ttls[redis_key] == 3600

    async def test_get_commitment(self, manager, fake_redis_client):
        key = "game:combat:snapshot:test"
        fake_redis_client.store[key] = {"meta": {"id": 1}}

        result = await manager.get_snapshot("test")
        assert result == {"meta": {"id": 1}}

    async def test_section_getters(self, manager, fake_redis_client):
        key = "game:combat:snapshot:test"
        fake_redis_client.store[key] = {
            "meta": {"m": 1},
            "runtime": {"r": 1},
            "combat": {"c": 1},
            "inventory": {"i": 1},
            "status": {"s": 1},
            "source": {"src": 1}
        }

        assert await manager.get_meta("test") == {"m": 1}
        assert await manager.get_runtime("test") == {"r": 1}
        assert await manager.get_combat("test") == {"c": 1}
        assert await manager.get_inventory("test") == {"i": 1}
        assert await manager.get_status("test") == {"s": 1}
        assert await manager.get_source("test") == {"src": 1}

    async def test_patch_section(self, manager, fake_redis_client):
        key = "game:combat:snapshot:test"
        fake_redis_client.store[key] = {"meta": {}}

        await manager.patch_section("test", "combat", {"hp": 50})
        assert fake_redis_client.store[key]["combat"] == {"hp": 50}

    async def test_touch_and_delete(self, manager, fake_redis_client):
        key = "game:combat:snapshot:test"
        fake_redis_client.store[key] = {"meta": {}}

        await manager.touch("test", 500)
        assert fake_redis_client.ttls[key] == 500

        await manager.delete_snapshot("test")
        assert key not in fake_redis_client.store

    async def test_redis_client_branch(self, manager):
        # Test the branch where self.redis has redis_client attribute
        class MockRedis:
            def __init__(self):
                self.redis_client = "client"

        mgr = ActorCommitmentManager(MockRedis())
        assert mgr._redis_client() == "client"

    async def test_redis_client_pipeline_branch(self, manager):
        # Test the branch where self.redis has pipeline.client
        class MockRedis:
            def __init__(self):
                self.pipeline = MagicMock()
                self.pipeline.client = "pipe_client"

        mgr = ActorCommitmentManager(MockRedis())
        assert mgr._redis_client() == "pipe_client"

    async def test_save_commitments_with_falsy_result(self, manager, fake_redis_client):
        # Force a falsy result (not Exception, but e.g. None or False)
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[False, True])
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=None)
        mock_pipe.json = MagicMock(return_value=mock_pipe)

        mocker_local = MagicMock()
        mocker_local.pipeline = MagicMock(return_value=mock_pipe)

        with pytest.MonkeyPatch().context() as m:
            m.setattr(manager, "_redis_client", lambda: mocker_local)
            saved = await manager.save_snapshots({"a": {"meta": {}}})
            assert saved == {} # because set_result was False

    async def test_pipeline_exception_handling(self, manager, mocker):
        # Mock _redis_client to raise an exception when pipeline() is called
        mocker.patch.object(manager, "_redis_client", side_effect=Exception("pipeline fail"))

        assert await manager.save_snapshots({"a": {}}) == {}
        assert await manager.get_snapshots_batch(["k"]) == {"k": None}
        assert await manager.get_sections_batch(["k"], "meta") == {"k": None}

    async def test_empty_inputs(self, manager):
        assert await manager.save_snapshots({}) == {}
        assert await manager.get_snapshots_batch([]) == {}
        assert await manager.get_sections_batch([], "meta") == {}

    def test_actor_refs_are_standardized(self, manager):
        assert manager.source_ref("player", 7) == "player:7"
        assert manager.source_ref("monster", "m1") == "monster:m1"
        assert manager.actor_uuid("player", 7, "combat-1") == manager.actor_uuid("player", 7, "combat-1")
        assert manager.actor_uuid("player", 7, "combat-1") != manager.actor_uuid("player", 7, "combat-2")
        assert manager.actor_uuid("player", 7) != manager.actor_uuid("player", 7)

    def test_first_edge_cases(self, manager):
        assert manager._first([]) is None
        assert manager._first([None]) is None
        assert manager._first([{"a": 1}]) == {"a": 1}
        assert manager._first({"a": 1}) == {"a": 1}
        assert manager._first("not a dict") is None

def test_resolve_sections_include_exclude_and_forced_meta_source() -> None:
    assert resolve_sections({"combat"}, set()) == {"combat", "meta", "source"}
    assert "inventory" not in resolve_sections(None, {"inventory"})
    assert resolve_sections(set(), {"meta", "source"}) == {"meta", "source"}
