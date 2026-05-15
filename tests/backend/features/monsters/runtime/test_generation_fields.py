import pytest

from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
from src.backend.features.monsters.dto.resources import MonsterFamilyDTO
from src.backend.features.monsters.runtime.generation_fields import (
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
            "skill_kit": {
                "base": {"skill_fencing": 0.2},
                "role_bonus": {"minion": {}, "boss": {"skill_tactics": 0.3}},
            },
            "clan_model": {
                "balance": {"organization_divisor": 5.0, "composition_profile": "many_weak"},
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
                    "skill_profile": {"base": {"skill_light_armor": 0.05}},
                    "ai_profile": {"behavior": "swarm_chaff"},
                }
            ],
            "variants": {
                "sewer_rat": {
                    "id": "sewer_rat",
                    "role": "minion",
                    "cost": 20,
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
                    "skill_overrides": {"skill_fencing": 0.25},
                },
                "rat_king": {
                    "id": "rat_king",
                    "role": "boss",
                    "cost": 600,
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

    skills = build_scaled_skills(family, variant, member_model)
    abilities = build_granted_abilities(family, variant, member_model)

    assert skills.skills == {"skill_fencing": 0.25, "skill_light_armor": 0.05}
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
        generation={"item_grade": "artifact", "rarity_tier": 1},
    )

    projection = build_items([item], owner_key="member_0")

    assert projection.layout.equipment == {"main_hand": "item-1"}
    assert projection.by_id["item-1"]["combat"]["bonuses"] == {"main_hand_accuracy": "+0.01"}


@pytest.mark.unit
def test_build_text_payload_maps_ai_encounter_fields() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]

    text = build_text_payload(
        variant,
        {
            "name": "Канализационная крыса",
            "appearance": "Крыса с мокрой серой шерстью.",
            "detected": "Она пятится к трубе, не отрывая взгляда.",
            "ambush": "Она бросается из темной щели.",
            "idle": "Она грызет обломок кожи у стены.",
        },
    )

    assert text.name_ru == "Канализационная крыса"
    assert text.appearance_ru == "Крыса с мокрой серой шерстью."
    assert text.detected_ru == "Она пятится к трубе, не отрывая взгляда."
    assert text.ambush_ru == "Она бросается из темной щели."
    assert text.idle_ru == "Она грызет обломок кожи у стены."


@pytest.mark.unit
def test_build_text_payload_keeps_legacy_encounter_compatible() -> None:
    family = _family()
    variant = family.variants["sewer_rat"]

    text = build_text_payload(
        variant,
        {
            "name": "Крыса",
            "appearance": "Тощая крыса.",
            "encounter": "Крыса выскакивает на свет.",
            "behavior": "Она жмется к стенам.",
        },
    )

    assert text.detected_ru == "Крыса выскакивает на свет."
    assert text.ambush_ru == "Крыса выскакивает на свет."
    assert text.idle_ru == "Она жмется к стенам."


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
    assert template.balance.base_cost == 20
    assert template.balance.effective_cost == 4
