from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.actor_state.runtime.assemblers.monster_assembler import build_snapshots
from src.backend.features.actor_state.runtime.sections import COMBAT, INVENTORY, RUNTIME, STATUS


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
            loadout_ids=["item1"],
        )
        mocker.patch(
            "src.backend.features.actor_state.runtime.assemblers.monster_assembler.get_monster_repo",
            return_value=MagicMock(get_monsters_batch=AsyncMock(return_value=[monster])),
        )

        sections = {COMBAT, INVENTORY, STATUS, RUNTIME}
        result = await build_snapshots(session, [m1_id, unknown_id], sections)

        assert m1_id in result
        assert unknown_id not in result
        snap = result[m1_id]
        assert snap["meta"]["name"] == "Monster"
        assert snap["combat"]["math_model"]["attributes"]["str"]["base"] == 10
        assert "ability1" in snap["combat"]["loadout"]["abilities"]
        assert snap["status"]["hp_current"] > 0

    def test_ability_ids_list(self, mocker):
        from src.backend.features.actor_state.runtime.assemblers.monster_assembler import _ability_ids

        snapshot = [{"id": "a1"}, "a2"]
        assert _ability_ids(snapshot) == ["a1", "a2"]

    async def test_build_snapshots_from_generated_monster_rows(self, session, mocker):
        from src.backend.features.monsters.dto.generation import MonsterGenerationContext
        from src.backend.features.monsters.runtime.clan_factory import ClanFactory
        from src.backend.features.monsters.runtime.hashing import (
            compute_context_hash,
            compute_unique_clan_hash,
            normalize_tags,
        )

        context = MonsterGenerationContext(zone_id="D4_0_1", biome_id="forest", tier=1, tags=["mana_leak"])
        tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, tags)
        family_id = ClanFactory().select_family_id(context, context_hash)
        clan, members = ClanFactory().build_clan_with_members(
            family_id=family_id,
            context=context,
            context_hash=context_hash,
            unique_hash=compute_unique_clan_hash(family_id, context_hash),
            normalized_tags=tags,
        )
        monster = members[0]
        monster.clan = clan
        mocker.patch(
            "src.backend.features.actor_state.runtime.assemblers.monster_assembler.get_monster_repo",
            return_value=MagicMock(get_monsters_batch=AsyncMock(return_value=[monster])),
        )

        result = await build_snapshots(session, [str(monster.id)], {COMBAT, STATUS})

        snapshot = result[str(monster.id)]
        assert snapshot["source"]["clan_id"] == str(clan.id)
        assert snapshot["combat"]["math_model"]["attributes"]
        assert "layout" in snapshot["combat"]["loadout"]
        assert "known_abilities" in snapshot["combat"]["loadout"]
        assert snapshot["combat"]["skills"]
        assert snapshot["source"]["db_refs"]["generated_monsters"] == str(monster.id)
