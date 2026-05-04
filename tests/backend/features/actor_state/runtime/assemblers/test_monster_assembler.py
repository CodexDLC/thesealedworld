import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.features.actor_state.runtime.assemblers.monster_assembler import build_snapshots
from src.backend.features.actor_state.runtime.sections import COMBAT, INVENTORY, STATUS, RUNTIME

@pytest.mark.unit
class TestMonsterAssembler:
    @pytest.fixture
    def session(self):
        return MagicMock()

    async def test_build_snapshots_empty(self, session):
        assert await build_snapshots(session, [], []) == {}

    async def test_build_snapshots_full(self, session, mocker):
        import uuid
        m1_id = str(uuid.uuid4())
        unknown_id = str(uuid.uuid4())

        monster = MagicMock(
            id=m1_id,
            name_ru="Monster",
            role="boss",
            variant_key="v1",
            clan_id="c1",
            scaled_base_stats={"str": 10},
            skills_snapshot={"ability1": {}},
            loadout_ids=["item1"]
        )
        mocker.patch("src.backend.features.actor_state.runtime.assemblers.monster_assembler.get_monster_repo",
                     return_value=MagicMock(get_monsters_batch=AsyncMock(return_value=[monster])))

        sections = {COMBAT, INVENTORY, STATUS, RUNTIME}
        result = await build_snapshots(session, [m1_id, unknown_id], sections)

        assert m1_id in result
        assert unknown_id not in result
        snap = result[m1_id]
        assert snap["meta"]["name"] == "Monster"
        assert snap["combat"]["math_model"]["attributes"]["str"]["base"] == 10
        assert "ability1" in snap["combat"]["loadout"]["abilities"]
        assert snap["status"]["hp_current"] == -1

    def test_ability_ids_list(self, mocker):
        from src.backend.features.actor_state.runtime.assemblers.monster_assembler import _ability_ids
        snapshot = [{"id": "a1"}, "a2"]
        assert _ability_ids(snapshot) == ["a1", "a2"]
