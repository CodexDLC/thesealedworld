import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder


def _clan() -> GeneratedClan:
    return GeneratedClan(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        identity_hash="identity",
        context_identity={"tier": 1},
        context_hash="context",
        selected_traits=[
            {
                "key": "rot_adapted",
                "modifiers": [{"target": "hp", "base": 4.0, "per_tier": 2.0}],
            }
        ],
        title="Rat Swarm",
        description="Rat Swarm",
        encounter_texts={},
        generation_version=2,
        resource_version="1",
    )


def _monster(active_snapshot: dict) -> GeneratedMonster:
    clan = _clan()
    monster = GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan.id,
        variant_id="sewer_rat",
        member_hash="sewer-rat",
        role="minion",
        title="Sewer Rat",
        short_description="Sewer Rat",
        min_tier=1,
        max_tier=3,
        mongo_actor_key=f"actor:{clan.id}:sewer_rat:sewer-rat",
        active_snapshot=active_snapshot,
        actor_document={"tier_snapshots": {"tier_1": active_snapshot}},
    )
    monster.clan = clan
    return monster


def test_monster_combat_actor_input_uses_prebuilt_tier_snapshot() -> None:
    combat_input = {
        "meta": {"actor_type": "monster", "actor_id": "m1", "snapshot_tier": 1},
        "source": {"monster_id": "m1", "mongo_actor_key": "actor:m1"},
        "status": {"hp": {"current": 20, "max": 20}},
        "raw": {"modifiers": {"hp": {"base": 10, "source": {}, "temp": {}}}},
        "skills": {"skill_unarmed": 0.2},
        "loadout": {"layout": {"main_hand": "skill_unarmed"}},
    }

    snapshot = MonsterCombatActorInputBuilder().build_snapshot(
        _monster({"snapshot_tier": 1, "combat_snapshot_input": combat_input})
    )

    assert snapshot["meta"] == combat_input["meta"]
    assert snapshot["source"] == combat_input["source"]
    assert snapshot["status"] == combat_input["status"]
    assert snapshot["combat"]["math_model"] == combat_input["raw"]
    assert snapshot["combat"]["skills"] == combat_input["skills"]
    assert snapshot["combat"]["loadout"] == combat_input["loadout"]


def test_monster_combat_actor_input_fails_without_prebuilt_snapshot() -> None:
    with pytest.raises(ValueError, match="combat_snapshot_input"):
        MonsterCombatActorInputBuilder().build_snapshot(_monster({"snapshot_tier": 1}))


def test_monster_combat_actor_input_does_not_apply_clan_traits_at_runtime() -> None:
    combat_input = {
        "meta": {"actor_type": "monster", "actor_id": "m1", "snapshot_tier": 1},
        "source": {"monster_id": "m1"},
        "status": {},
        "raw": {"modifiers": {"hp": {"base": 10, "source": {}, "temp": {}}}},
        "skills": {},
        "loadout": {},
    }

    snapshot = MonsterCombatActorInputBuilder().build_snapshot(
        _monster({"snapshot_tier": 1, "combat_snapshot_input": combat_input})
    )

    hp_sources = snapshot["combat"]["math_model"]["modifiers"]["hp"]["source"]
    assert "clan_trait:rot_adapted" not in hp_sources
