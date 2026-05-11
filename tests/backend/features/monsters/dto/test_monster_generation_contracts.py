import pytest
from pydantic import ValidationError

from src.backend.features.monsters.dto.generation import GeneratedMonsterTemplateDTO
from src.backend.features.monsters.dto.resources import MonsterFamilyDTO


def test_generated_monster_template_accepts_target_json_contract() -> None:
    template = GeneratedMonsterTemplateDTO.model_validate(
        {
            "variant_key": "sewer_rat",
            "role": "minion",
            "member_tier": 1,
            "text_content": {"name_ru": "Крыса"},
            "meta": {"archetype": "beast", "tags": ["monster", "rat"]},
            "scaled_attributes": {
                "strength": 4,
                "agility": 12,
                "endurance": 6,
                "intellect": 1,
                "memory": 1,
                "mental": 2,
                "perception": 7,
                "projection": 1,
                "prediction": 2,
            },
            "scaled_skills": {"skills": {"skill_daggers": 0.2, "skill_light_armor": 0.05}},
            "items": {
                "layout": {"equipment": {"main_hand": "monster_item:rat:main_hand"}, "belt": {}},
                "by_id": {
                    "monster_item:rat:main_hand": {
                        "item_id": "monster_item:rat:main_hand",
                        "base_id": "dagger",
                    }
                },
            },
            "granted_abilities": {"known_abilities": []},
            "ai_profile": {"behavior": "swarm_chaff"},
            "balance": {
                "base_cost": 20,
                "effective_cost": 4,
                "threat_rating": 20,
                "organization_type": "swarm",
                "organization_divisor": 5.0,
            },
        }
    )

    assert template.variant_key == "sewer_rat"
    assert template.scaled_skills.skills["skill_daggers"] == 0.2
    assert "monster_item:rat:main_hand" in template.items.by_id


def test_generated_monster_template_rejects_missing_item_projection() -> None:
    with pytest.raises(ValidationError, match="layout references missing by_id entries"):
        GeneratedMonsterTemplateDTO.model_validate(
            {
                "variant_key": "sewer_rat",
                "role": "minion",
                "member_tier": 1,
                "meta": {"archetype": "beast"},
                "scaled_attributes": {
                    "strength": 4,
                    "agility": 12,
                    "endurance": 6,
                    "intellect": 1,
                    "memory": 1,
                    "mental": 2,
                    "perception": 7,
                    "projection": 1,
                    "prediction": 2,
                },
                "items": {"layout": {"equipment": {"main_hand": "missing_item"}}, "by_id": {}},
                "balance": {
                    "base_cost": 20,
                    "effective_cost": 4,
                    "threat_rating": 20,
                    "organization_type": "swarm",
                    "organization_divisor": 5.0,
                },
            }
        )


def test_monster_family_accepts_clan_and_member_resource_models() -> None:
    family = MonsterFamilyDTO.model_validate(
        {
            "id": "rat_swarm",
            "archetype": "beast",
            "organization_type": "swarm",
            "default_tags": ["rat"],
            "hierarchy": {"minions": ["sewer_rat"], "veterans": [], "elites": [], "boss": []},
            "clan_model": {
                "tier_range": {"min_tier": 0, "max_tier": 4},
                "balance": {
                    "organization_divisor": 5.0,
                    "composition_profile": "many_weak_one_support",
                    "max_elites_without_boss": 1,
                    "boss_allowed": False,
                },
                "item_mappings": {
                    "rat_bite_claws": {
                        "equipment_key": "rat_bite_claws",
                        "source_base_id": "dagger",
                        "slots": ["main_hand"],
                    }
                },
            },
            "member_models": [
                {
                    "variant_key": "sewer_rat",
                    "role": "minion",
                    "member_tier_offset": -1,
                    "skill_profile": {"base": {"skill_daggers": 0.2}},
                    "item_loadout_profile": {"main_hand": "rat_bite_claws"},
                }
            ],
            "variants": {
                "sewer_rat": {
                    "id": "sewer_rat",
                    "role": "minion",
                    "narrative_hint": "Small diseased rat.",
                    "cost": 20,
                    "base_stats": {
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
                    "fixed_loadout": {},
                    "skills": [],
                }
            },
        }
    )

    assert family.clan_model is not None
    assert family.clan_model.balance.organization_divisor == 5.0
    assert family.member_models[0].variant_key == "sewer_rat"


def test_monster_family_rejects_member_model_for_missing_variant() -> None:
    with pytest.raises(ValidationError, match="member models reference missing variants"):
        MonsterFamilyDTO.model_validate(
            {
                "id": "rat_swarm",
                "archetype": "beast",
                "organization_type": "swarm",
                "default_tags": ["rat"],
                "hierarchy": {"minions": ["sewer_rat"]},
                "member_models": [{"variant_key": "ghost_rat", "role": "minion"}],
                "variants": {
                    "sewer_rat": {
                        "id": "sewer_rat",
                        "role": "minion",
                        "narrative_hint": "Small diseased rat.",
                        "cost": 20,
                        "base_stats": {
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
                        "fixed_loadout": {},
                        "skills": [],
                    }
                },
            }
        )
