import pytest

from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.dto.resources import MonsterFamilyDTO
from src.backend.features.monsters.resources import get_all_family_configs
from src.backend.features.monsters.runtime.generation_fields import (
    ORGANIZATION_GS_DIVISORS,
    build_balance,
    build_generated_monster_template,
    build_granted_abilities,
    build_items,
    build_member_tier,
    build_scaled_attributes,
    build_scaled_skills,
    build_text_payload,
)


def _family() -> MonsterFamilyDTO:
    return MonsterFamilyDTO.model_validate(
        {
            "id": "rat_swarm",
            "archetype": "beast",
            "organization_type": "swarm",
            "default_tags": ["beast", "rat"],
            "hierarchy": {"minions": ["sewer_rat"], "veterans": [], "elites": [], "boss": ["rat_king"]},
            "clan_model": {
                "balance": {"organization_divisor": 4.0, "composition_profile": "many_weak"},
                "ai_defaults": {"targeting": "lowest_hp", "group_logic": "swarm"},
            },
            "member_models": [
                {
                    "variant_key": "sewer_rat",
                    "role": "minion",
                    "member_tier_offset": 0,
                    "attribute_profile": {
                        "flat_bonus": {"agility": 1},
                        "tier_bonus": {"endurance": 2},
                    },
                    "skill_profile": {"base": ["skill_light_armor"]},
                    "ai_profile": {"behavior": "swarm_chaff"},
                }
            ],
            "variants": {
                "sewer_rat": {
                    "id": "sewer_rat",
                    "role": "minion",
                    "spawn_weight": 20,
                    "min_tier": 0,
                    "max_tier": 3,
                    "narrative_hint": "Small diseased rat.",
                    "extra_tags": ["weak"],
                    "base_stats": {
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
                    "skills": ["skill_fencing", "skill_hunting"],
                },
                "rat_king": {
                    "id": "rat_king",
                    "role": "boss",
                    "spawn_weight": 600,
                    "min_tier": 4,
                    "max_tier": 7,
                    "narrative_hint": "A horrific amalgamation.",
                    "base_stats": {
                        "strength": 20,
                        "agility": 10,
                        "endurance": 35,
                        "intellect": 14,
                        "memory": 12,
                        "mental": 20,
                        "perception": 15,
                        "projection": 15,
                        "prediction": 5,
                    },
                },
            },
        }
    )


@pytest.mark.unit
def test_build_member_tier_uses_clan_tier_without_variant_bounds() -> None:
    family = _family()
    minion = family.variants["sewer_rat"]
    boss = family.variants["rat_king"]

    assert build_member_tier(1, minion, family.member_models[0]) == 1
    assert build_member_tier(3, boss) == 3
    assert build_member_tier(10, boss) == 10


@pytest.mark.unit
def test_build_scaled_attributes_maps_player_attribute_keys_and_profiles() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]

    attrs = build_scaled_attributes(variant, member_tier=2, member_model=family.member_models[0])

    assert attrs.strength == 4
    assert attrs.agility == 11
    assert attrs.endurance == 9
    assert attrs.intellect == 1
    assert attrs.memory == 1
    assert attrs.mental == 2
    assert attrs.projection == 1
    assert attrs.prediction == 2


@pytest.mark.unit
def test_build_scaled_skills_and_granted_abilities_use_family_member_and_variant_inputs() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]
    member_model = family.member_models[0]

    skills = build_scaled_skills(family, variant, member_model, member_tier=2)
    abilities = build_granted_abilities(family, variant, member_model)

    assert skills.skills == {"skill_fencing": 0.2857, "skill_light_armor": 0.2857}
    assert abilities.known_abilities == []
    assert abilities.ability_presentations == {}


@pytest.mark.unit
def test_build_items_groups_runtime_projections_by_owner() -> None:
    item = RuntimeItemProjectionDTO(
        item_id="item-1",
        owner_key="member_0",
        base_id="dagger",
        item_type="weapon",
        slot="main_hand",
        combat={"power": 3, "bonuses": {"main_hand_accuracy": "+0.01"}},
        generation={"item_grade": "common", "affix_profile": "monster_equipment_4slot", "rarity_tier": 1},
    )

    projection = build_items([item], owner_key="member_0")

    assert projection.layout.equipment == {"main_hand": "item-1"}
    assert projection.by_id["item-1"]["combat"]["bonuses"] == {"main_hand_accuracy": "+0.01"}


@pytest.mark.unit
def test_build_text_payload_maps_minimal_member_fields() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]

    text = build_text_payload(
        variant,
        {
            "name": "Канализационная крыса",
            "short_description": "Крыса с мокрой серой шерстью.",
            "visual_hint": "мокрая серая шерсть, низкая стойка",
        },
    )

    assert text.name_ru == "Канализационная крыса"
    assert text.appearance_ru == "Крыса с мокрой серой шерстью."
    assert text.visual_hint == "мокрая серая шерсть, низкая стойка"
    assert "detected_ru" not in text.model_dump(mode="json")
    assert "ambush_ru" not in text.model_dump(mode="json")
    assert "idle_ru" not in text.model_dump(mode="json")


@pytest.mark.unit
def test_build_text_payload_does_not_keep_legacy_encounter_prose() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]

    text = build_text_payload(
        variant,
        {
            "name": "Крыса",
            "short_description": "Тощая крыса.",
            "encounter": "Крыса выскакивает на свет.",
            "behavior": "Она жмется к стенам.",
        },
    )

    payload = text.model_dump(mode="json")
    assert payload["appearance_ru"] == "Тощая крыса."
    assert "encounter" not in payload
    assert "detected_ru" not in payload
    assert "ambush_ru" not in payload
    assert "idle_ru" not in payload


@pytest.mark.unit
def test_build_generated_monster_template_composes_field_builders() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]
    member_model = family.member_models[0]

    template = build_generated_monster_template(
        family,
        variant,
        context_tier=2,
        owner_key="member_0",
        member_model=member_model,
        generated_text={"name_ru": "Крыса"},
        source={"clan_id": "clan-1"},
    )

    assert template.variant_key == "sewer_rat"
    assert template.member_tier == 2
    assert template.text_content.name_ru == "Крыса"
    assert template.meta.family_id == "rat_swarm"
    assert template.meta.source == {"clan_id": "clan-1"}
    assert template.ai_profile.behavior == "swarm_chaff"
    assert template.ai_profile.targeting == "lowest_hp"
    assert template.balance.organization_type == "swarm"
    assert template.balance.organization_divisor == 4.0
    assert "base_cost" not in template.balance.model_dump()
    assert "effective_cost" not in template.balance.model_dump()
    assert "threat_rating" not in template.balance.model_dump()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("organization_type", "expected_divisor"),
    sorted(ORGANIZATION_GS_DIVISORS.items()),
)
def test_build_balance_uses_default_organization_gs_divisors(
    organization_type: str,
    expected_divisor: float,
) -> None:
    family = MonsterFamilyDTO.model_validate(
        {
            "id": f"test_{organization_type}",
            "archetype": "beast",
            "organization_type": organization_type,
            "default_tags": [],
            "hierarchy": {"minions": ["test_var"], "veterans": [], "elites": [], "boss": []},
            "variants": {
                "test_var": {
                    "id": "test_var",
                    "role": "minion",
                    "spawn_weight": 100,
                    "min_tier": 0,
                    "max_tier": 5,
                    "narrative_hint": "test",
                    "base_stats": {
                        "strength": 5,
                        "agility": 5,
                        "endurance": 5,
                        "intellect": 1,
                        "memory": 1,
                        "mental": 2,
                        "perception": 5,
                        "projection": 1,
                        "prediction": 2,
                    },
                }
            },
        }
    )
    variant = family.variants["test_var"]

    balance = build_balance(family, variant)

    assert balance.organization_divisor == expected_divisor
    assert "base_cost" not in balance.model_dump()
    assert "effective_cost" not in balance.model_dump()
    assert "threat_rating" not in balance.model_dump()


@pytest.mark.unit
def test_all_monster_families_do_not_carry_static_family_modifiers() -> None:
    offenders: list[str] = []
    for family in get_all_family_configs().values():
        if hasattr(family, "family_modifiers"):
            offenders.append(family.id)

    assert offenders == []


@pytest.mark.unit
def test_generated_monster_template_does_not_include_family_modifiers() -> None:
    family = MonsterFamilyDTO.model_validate(
        {
            "id": "test_family",
            "archetype": "beast",
            "organization_type": "pack",
            "default_tags": [],
            "hierarchy": {"minions": ["test_var"], "veterans": [], "elites": [], "boss": []},
            "variants": {
                "test_var": {
                    "id": "test_var",
                    "role": "minion",
                    "spawn_weight": 20,
                    "min_tier": 0,
                    "max_tier": 5,
                    "narrative_hint": "test",
                    "base_stats": {
                        "strength": 5,
                        "agility": 5,
                        "endurance": 5,
                        "intellect": 1,
                        "memory": 1,
                        "mental": 2,
                        "perception": 5,
                        "projection": 1,
                        "prediction": 2,
                    },
                }
            },
        }
    )
    variant = family.variants["test_var"]

    template = build_generated_monster_template(family, variant, context_tier=7, owner_key="member-1")

    assert "family_modifiers" not in template.model_dump(mode="json")


@pytest.mark.unit
def test_build_scaled_skills_uses_declared_variant_skills_and_tier_value() -> None:
    family = MonsterFamilyDTO.model_validate(
        {
            "id": "test_family",
            "archetype": "humanoid",
            "organization_type": "gang",
            "default_tags": [],
            "hierarchy": {"minions": ["test_var"], "veterans": [], "elites": [], "boss": []},
            "variants": {
                "test_var": {
                    "id": "test_var",
                    "role": "minion",
                    "spawn_weight": 20,
                    "min_tier": 0,
                    "max_tier": 5,
                    "narrative_hint": "test",
                    "base_stats": {
                        "strength": 5,
                        "agility": 5,
                        "endurance": 5,
                        "intellect": 1,
                        "memory": 1,
                        "mental": 2,
                        "perception": 5,
                        "projection": 1,
                        "prediction": 2,
                    },
                    "skills": ["skill_tactics", "skill_fencing", "skill_scouting"],
                }
            },
        }
    )
    variant = family.variants["test_var"]

    skills = build_scaled_skills(family, variant, member_tier=1)

    assert skills.skills == {"skill_tactics": 0.1429, "skill_fencing": 0.1429}


@pytest.mark.unit
def test_bandit_poacher_skills_use_archery_and_ranged_combat() -> None:
    """bandit_poacher uses archery plus the ranged tactical style."""
    from src.backend.features.monsters.resources import get_family_config

    family = get_family_config("bandit_gang")
    assert family is not None, "bandit_gang family not found in registry"
    variant = family.variants.get("bandit_poacher")
    assert variant is not None, "bandit_poacher variant not found"

    skills = build_scaled_skills(family, variant, member_tier=1)

    assert "skill_archery" in skills.skills, "bandit_poacher must have skill_archery"
    assert "skill_ranged_combat" in skills.skills, "bandit_poacher must have the ranged tactical style"
