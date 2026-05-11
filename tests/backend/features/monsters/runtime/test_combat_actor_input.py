import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder


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
        "scaled_skills": {"skills": {"skill_fencing": 0.25, "skill_light_armor": 0.05}},
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
                        "triggers": ["crit.weapon_serrated_bleed_crit"],
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
        "granted_abilities": {
            "known_abilities": ["basic_attack"],
            "ability_presentations": {"basic_attack": "infected_bite"},
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
        threat_rating=20,
        name_ru="Крыса",
        description="Крыса",
        scaled_base_stats={
            "strength": 4,
            "agility": 10,
            "endurance": 5,
            "intelligence": 1,
            "wisdom": 1,
            "men": 2,
            "perception": 6,
            "charisma": 1,
            "luck": 2,
        },
        loadout_ids=template["items"],
        skills_snapshot=template["scaled_skills"],
        combat_seed={"schema_version": 2, "generated_template": template},
    )
    monster.clan = clan

    snapshot = MonsterCombatActorInputBuilder().build_snapshot(monster)

    assert set(snapshot) == {"meta", "source", "status", "combat"}
    assert snapshot["meta"]["actor_type"] == "monster"
    assert snapshot["meta"]["actor_id"] == str(monster_id)
    assert snapshot["meta"]["name"] == "Крыса с черными когтями"
    assert snapshot["source"]["monster_id"] == str(monster_id)
    assert snapshot["source"]["family_id"] == "rat_swarm"
    assert snapshot["status"]["hp"]["max"] > 0
    combat = snapshot["combat"]
    assert combat["math_model"]["attributes"]["strength"]["base"] == 4.0
    assert combat["math_model"]["modifiers"]["main_hand_damage_base"]["base"] == 7.0
    assert combat["math_model"]["modifiers"]["armor"]["base"] == 3.0
    assert combat["math_model"]["modifiers"]["main_hand_accuracy"]["source"]["item:claws-1"] == 0.02
    assert combat["skills"] == {"skill_fencing": 0.25, "skill_light_armor": 0.05}
    assert combat["loadout"]["layout"]["main_hand"] == "skill_fencing"
    assert combat["loadout"]["layout"]["main_hand_trigger"] == "crit.weapon_serrated_bleed_crit"
    assert combat["loadout"]["layout"]["body"] == "skill_light_armor"
    assert combat["loadout"]["known_abilities"] == ["basic_attack"]
    assert combat["loadout"]["ability_presentations"] == {"basic_attack": "infected_bite"}
