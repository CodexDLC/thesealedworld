import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder


def _make_clan(family_id: str = "bandit_gang") -> GeneratedClan:
    return GeneratedClan(
        id=uuid.uuid4(),
        family_id=family_id,
        tier=2,
        zone_id="zone-b",
        context_hash="ctx",
        unique_hash="uniq",
        raw_tags={},
        flavor_content={},
        name_ru="Клан",
        description="Клан",
    )


def _make_humanoid_monster(
    clan: GeneratedClan,
    *,
    weapon_power: int = 10,
    weapon_bonuses: dict | None = None,
    weapon_affixes: list | None = None,
) -> GeneratedMonster:
    monster_id = uuid.uuid4()
    monster = GeneratedMonster(
        id=monster_id,
        clan_id=clan.id,
        variant_key="bandit_thug",
        role="minion",
        member_tier=2,
        threat_rating=30,
        name_ru="Головорез",
        description="Головорез",
        text_content={"name_ru": "Головорез"},
        scaled_attributes={
            "strength": 12,
            "agility": 8,
            "endurance": 10,
            "intellect": 3,
            "memory": 2,
            "mental": 4,
            "perception": 5,
            "projection": 1,
            "prediction": 2,
        },
        scaled_skills={"skill_one_handed": 0.35, "skill_light_armor": 0.10},
        items={
            "layout": {"equipment": {"main_hand": "axe-1"}, "belt": {}},
            "by_id": {
                "axe-1": {
                    "item_id": "axe-1",
                    "owner_key": "member-0",
                    "base_id": "hand_axe",
                    "item_type": "weapon",
                    "slot": "main_hand",
                    "combat": {
                        "power": weapon_power,
                        "damage_spread": 0.2,
                        "implicit_bonuses": {},
                        "bonuses": weapon_bonuses or {},
                        "triggers": [],
                        "tags": [],
                        "related_skill": "skill_one_handed",
                    },
                    "generation": {
                        "item_grade": "uncommon",
                        "rarity_tier": 2,
                        "affixes": weapon_affixes or [],
                    },
                }
            },
        },
        vitals={
            "hp": {"current": 40, "max": 40},
            "energy": {"current": 15, "max": 15},
            "stamina": {"current": 15, "max": 15},
        },
        ai_profile={"behavior": "melee_fighter"},
        generation_meta={
            "schema_version": 2,
            "visual": {
                "status": "fallback",
                "image_url": "/static/images/monsters/families/bandit_gang.svg",
                "fallback_image_url": "/static/images/monsters/families/bandit_gang.svg",
                "storage_key": "monsters/generated/families/test.webp",
            },
            "meta": {
                "archetype": "humanoid",
                "family_id": clan.family_id,
                "tags": ["monster", "bandit", "minion"],
                "source": {"owner_key": "member-0"},
            },
            "source": {"owner_key": "member-0"},
            "balance": {
                "base_cost": 30,
                "effective_cost": 10,
                "threat_rating": 30,
                "organization_type": "gang",
                "organization_divisor": 3,
            },
        },
    )
    monster.clan = clan
    return monster


@pytest.mark.unit
def test_monster_combat_actor_input_uses_generated_template_contract() -> None:
    clan_id = uuid.uuid4()
    monster_id = uuid.uuid4()
    clan = GeneratedClan(
        id=clan_id,
        family_id="rat_swarm",
        tier=1,
        zone_id="zone-a",
        context_hash="ctx",
        unique_hash="uniq",
        raw_tags={},
        flavor_content={},
        name_ru="Рой",
        description="Рой",
    )
    template = {
        "schema_version": 1,
        "variant_key": "sewer_rat",
        "role": "minion",
        "member_tier": 1,
        "text_content": {"name_ru": "Крыса с черными когтями"},
        "meta": {
            "archetype": "beast",
            "family_id": "rat_swarm",
            "tags": ["monster", "rat", "minion"],
            "source": {"owner_key": "member-1"},
        },
        "scaled_attributes": {
            "strength": 4,
            "agility": 10,
            "endurance": 5,
            "intellect": 1,
            "memory": 1,
            "mental": 2,
            "perception": 6,
            "projection": 1,
            "prediction": 2,
        },
        "scaled_skills": {
            "skills": {
                "skill_fencing": 0.25,
                "skill_light_armor": 0.05,
                "skill_scouting": 0.9,
                "skill_adaptation": 0.8,
            }
        },
        "items": {
            "layout": {
                "equipment": {"main_hand": "claws-1", "chest_armor": "hide-1"},
                "belt": {},
            },
            "by_id": {
                "claws-1": {
                    "item_id": "claws-1",
                    "owner_key": "member-1",
                    "base_id": "dagger",
                    "item_type": "weapon",
                    "slot": "main_hand",
                    "combat": {
                        "power": 7,
                        "damage_spread": 0.2,
                        "implicit_bonuses": {},
                        "bonuses": {"main_hand_accuracy": "+0.02"},
                        "triggers": ["crit.weapon_flat_armor_gap_crit"],
                        "tags": ["natural_weapon"],
                        "related_skill": "skill_fencing",
                    },
                    "generation": {"item_grade": "artifact", "rarity_tier": 1, "affixes": []},
                },
                "hide-1": {
                    "item_id": "hide-1",
                    "owner_key": "member-1",
                    "base_id": "leather_armor",
                    "item_type": "armor",
                    "slot": "chest_armor",
                    "combat": {
                        "power": 3,
                        "damage_spread": 0,
                        "implicit_bonuses": {},
                        "bonuses": {},
                        "triggers": [],
                        "tags": ["natural_armor"],
                        "related_skill": "skill_light_armor",
                    },
                    "generation": {"item_grade": "artifact", "rarity_tier": 1, "affixes": []},
                },
            },
        },
        "ai_profile": {"behavior": "swarm_chaff"},
        "balance": {
            "base_cost": 20,
            "effective_cost": 4,
            "threat_rating": 20,
            "organization_type": "swarm",
            "organization_divisor": 5,
        },
    }
    monster = GeneratedMonster(
        id=monster_id,
        clan_id=clan_id,
        variant_key="sewer_rat",
        role="minion",
        member_tier=1,
        threat_rating=20,
        name_ru="Крыса с черными когтями",
        description="Крыса",
        text_content=template["text_content"],
        scaled_attributes=template["scaled_attributes"],
        scaled_skills=template["scaled_skills"]["skills"],
        items=template["items"],
        vitals={
            "hp": {"current": 20, "max": 20},
            "energy": {"current": 10, "max": 10},
            "stamina": {"current": 10, "max": 10},
        },
        ai_profile=template["ai_profile"],
        generation_meta={
            "schema_version": 2,
            "visual": {
                "status": "fallback",
                "image_url": "/static/images/monsters/families/rat_swarm.svg",
                "fallback_image_url": "/static/images/monsters/families/rat_swarm.svg",
                "storage_key": "monsters/generated/families/test.webp",
            },
            "meta": template["meta"],
            "source": template["meta"]["source"],
            "balance": template["balance"],
        },
    )
    monster.clan = clan

    snapshot = MonsterCombatActorInputBuilder().build_snapshot(monster)

    assert set(snapshot) == {"meta", "source", "status", "combat"}
    assert snapshot["meta"]["actor_type"] == "monster"
    assert snapshot["meta"]["actor_id"] == str(monster_id)
    assert snapshot["meta"]["name"] == "Крыса с черными когтями"
    assert snapshot["meta"]["avatar_url"] == "/static/images/monsters/families/rat_swarm.svg"
    assert snapshot["source"]["monster_id"] == str(monster_id)
    assert snapshot["source"]["family_id"] == "rat_swarm"
    assert snapshot["source"]["visual"]["status"] == "fallback"
    assert snapshot["status"]["hp"]["max"] > 0
    combat = snapshot["combat"]
    assert combat["math_model"]["attributes"]["strength"]["base"] == 4.0
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] == 7.0
    assert combat["math_model"]["modifiers"]["armor"]["base"] == 3.0
    assert combat["math_model"]["modifiers"]["main_hand_accuracy"]["source"]["item:claws-1"] == 0.02
    assert combat["skills"] == {"skill_fencing": 0.25, "skill_light_armor": 0.05}
    assert combat["loadout"]["layout"]["main_hand"] == "skill_fencing"
    assert combat["loadout"]["layout"]["main_hand_trigger"] == "crit.weapon_flat_armor_gap_crit"
    assert combat["loadout"]["layout"]["body"] == "skill_light_armor"
    assert combat["loadout"]["combat_surfaces"]["main_hand"] == {
        "slot": "main_hand",
        "delivery": "natural",
        "surface": "natural_weapon",
        "tags": ["natural_weapon"],
        "item_id": "claws-1",
        "base_id": "dagger",
        "skill_key": "skill_fencing",
    }
    assert combat["loadout"]["known_abilities"] == []


@pytest.mark.unit
def test_monster_with_affixed_item_preserves_bonuses() -> None:
    """Bug 1 regression: non-empty generation.affixes must NOT clear combat.bonuses."""
    clan = _make_clan()
    monster = _make_humanoid_monster(
        clan,
        weapon_power=10,
        weapon_bonuses={"main_hand_accuracy": "+0.05"},
        weapon_affixes=[{"affix_id": "accuracy_bonus", "tier": 1}],
    )

    snapshot = MonsterCombatActorInputBuilder().build_snapshot(monster)

    modifiers = snapshot["combat"]["math_model"]["modifiers"]
    assert "main_hand_accuracy" in modifiers, "main_hand_accuracy modifier missing — bonus was wiped (Bug 1)"
    sources = modifiers["main_hand_accuracy"].get("source", {})
    assert any("axe-1" in k for k in sources), "item bonus source missing from main_hand_accuracy"


@pytest.mark.unit
def test_humanoid_monster_has_nonzero_damage_potential() -> None:
    """Humanoid monster with a melee weapon must produce main_hand_damage_base > 0."""
    clan = _make_clan()
    monster = _make_humanoid_monster(clan, weapon_power=10)

    snapshot = MonsterCombatActorInputBuilder().build_snapshot(monster)

    combat = snapshot["combat"]
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] == 10.0
    assert "main_hand" in combat["loadout"]["combat_surfaces"]
    assert combat["loadout"]["combat_surfaces"]["main_hand"]["delivery"] == "weapon"
