import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.features.actor_state.runtime.assemblers.player_assembler import build_snapshots, _get_vitals_batch
from src.backend.features.actor_state.runtime.sections import COMBAT, INVENTORY, STATUS, RUNTIME

@pytest.mark.unit
class TestPlayerAssembler:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def redis(self, fake_redis_service):
        return fake_redis_service

    async def test_build_snapshots_empty(self, session, redis):
        assert await build_snapshots(session, redis, [], []) == {}

    async def test_build_snapshots_no_existing_chars(self, session, redis, mocker):
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.get_actor_state_character_repo",
                     return_value=MagicMock(get_characters_batch=AsyncMock(return_value=[])))
        assert await build_snapshots(session, redis, [1], []) == {}

    async def test_build_snapshots_full(self, session, redis, mocker):
        # Mock repos
        uuid_val = uuid.uuid4()
        char = MagicMock(character_id=1, user_id=uuid_val, location_id="loc1", game_stage=1, vitals_snapshot={"hp": 100})
        char.name = "Hero"
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.get_actor_state_character_repo",
                     return_value=MagicMock(get_characters_batch=AsyncMock(return_value=[char])))

        attr = MagicMock(character_id=1)
        attr.model_dump.return_value = {"strength": 10}
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.get_actor_state_attributes_repo",
                     return_value=MagicMock(get_attributes_batch=AsyncMock(return_value=[attr])))

        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.get_actor_state_skill_repo",
                     return_value=MagicMock(get_all_skills_progress_batch=AsyncMock(return_value={1: []})))

        # Mock symbiote
        symbiote = MagicMock(character_id=1, symbiote_name="S1", gift_id="G1", gift_rank=1, gift_xp=0, elements_resonance={})
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.get_actor_state_symbiote_repo",
                     return_value=MagicMock(get_symbiotes_batch=AsyncMock(return_value=[symbiote])))

        item = {"inventory_id": "i1", "data": {"power": 5, "implicit_bonuses": {"dex": 2}}, "quick_slot_position": 1}
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler.get_actor_state_inventory_repo",
                     return_value=MagicMock(get_items_by_location_batch=AsyncMock(return_value={1: [item]})))

        # Test with vitals missing from redis
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.player_assembler._get_vitals_batch",
                     AsyncMock(return_value={1: None}))

        sections = {COMBAT, INVENTORY, STATUS, RUNTIME}
        result = await build_snapshots(session, redis, [1], sections)

        snap = result[1]
        assert snap["source"]["symbiote"]["symbiote_name"] == "S1"
        assert snap["combat"]["math_model"]["modifiers"]["dex"]["source"]["item:i1"] == 2
        assert snap["status"]["hp"] == 100 # from char.vitals_snapshot

    async def test_get_vitals_batch_success(self, redis, fake_redis_client):
        from src.backend.infrastructure.redis.keys import PlayerCoreKey
        key = PlayerCoreKey().build(char_id=1)
        fake_redis_client.store[key] = {"vitals": {"hp": 80}}

        result = await _get_vitals_batch(redis, [1])
        assert result[1] == {"vitals": {"hp": 80}}

    async def test_get_vitals_batch_failure(self, redis, mocker):
        # Mock redis_client to raise exception
        mocker.patch.object(redis, "redis_client", MagicMock(pipeline=MagicMock(side_effect=Exception("fail"))))

        result = await _get_vitals_batch(redis, [1])
        assert result[1] is None

import uuid
