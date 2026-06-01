import pytest

from src.backend.features.character.resources.starting_imprints import ATTRIBUTE_KEYS
from src.backend.features.character.resources import STARTING_IMPRINTS
from src.backend.features.character.services import StartingImprintService

EXPECTED_MANUAL_ATTRIBUTES = {
    "starter_guard_01": {
        "strength": 17,
        "agility": 14,
        "endurance": 16,
        "intellect": 10,
        "memory": 11,
        "mental": 13,
        "perception": 15,
        "projection": 9,
        "prediction": 12,
    },
    "starter_breaker_01": {
        "strength": 17,
        "agility": 13,
        "endurance": 16,
        "intellect": 9,
        "memory": 10,
        "mental": 14,
        "perception": 12,
        "projection": 11,
        "prediction": 15,
    },
    "starter_duelist_01": {
        "strength": 16,
        "agility": 17,
        "endurance": 11,
        "intellect": 9,
        "memory": 12,
        "mental": 10,
        "perception": 15,
        "projection": 13,
        "prediction": 14,
    },
    "starter_dual_blades_01": {
        "strength": 15,
        "agility": 17,
        "endurance": 11,
        "intellect": 10,
        "memory": 13,
        "mental": 9,
        "perception": 16,
        "projection": 12,
        "prediction": 14,
    },
    "starter_dual_sword_01": {
        "strength": 17,
        "agility": 16,
        "endurance": 14,
        "intellect": 9,
        "memory": 13,
        "mental": 10,
        "perception": 15,
        "projection": 11,
        "prediction": 12,
    },
    "starter_dual_mace_01": {
        "strength": 17,
        "agility": 13,
        "endurance": 16,
        "intellect": 9,
        "memory": 14,
        "mental": 12,
        "perception": 15,
        "projection": 10,
        "prediction": 11,
    },
    "starter_pathfinder_01": {
        "strength": 15,
        "agility": 17,
        "endurance": 10,
        "intellect": 11,
        "memory": 13,
        "mental": 9,
        "perception": 16,
        "projection": 12,
        "prediction": 14,
    },
    "starter_hunter_01": {
        "strength": 15,
        "agility": 17,
        "endurance": 11,
        "intellect": 12,
        "memory": 13,
        "mental": 10,
        "perception": 16,
        "projection": 9,
        "prediction": 14,
    },
    "starter_archer_01": {
        "strength": 16,
        "agility": 17,
        "endurance": 11,
        "intellect": 12,
        "memory": 13,
        "mental": 10,
        "perception": 15,
        "projection": 9,
        "prediction": 14,
    },
    "starter_marksman_01": {
        "strength": 16,
        "agility": 15,
        "endurance": 14,
        "intellect": 12,
        "memory": 11,
        "mental": 10,
        "perception": 17,
        "projection": 9,
        "prediction": 13,
    },
    "starter_staff_01": {
        "strength": 16,
        "agility": 14,
        "endurance": 17,
        "intellect": 10,
        "memory": 11,
        "mental": 9,
        "perception": 15,
        "projection": 12,
        "prediction": 13,
    },
    "starter_heavy_guard_01": {
        "strength": 17,
        "agility": 12,
        "endurance": 16,
        "intellect": 9,
        "memory": 11,
        "mental": 15,
        "perception": 13,
        "projection": 10,
        "prediction": 14,
    },
    "starter_tactician_01": {
        "strength": 15,
        "agility": 14,
        "endurance": 10,
        "intellect": 12,
        "memory": 13,
        "mental": 11,
        "perception": 17,
        "projection": 9,
        "prediction": 16,
    },
    "starter_rift_survivor_01": {
        "strength": 16,
        "agility": 15,
        "endurance": 17,
        "intellect": 9,
        "memory": 12,
        "mental": 10,
        "perception": 14,
        "projection": 11,
        "prediction": 13,
    },
}


@pytest.mark.unit
def test_starting_imprint_builds_complete_guard_payload() -> None:
    build = StartingImprintService().build("starter_guard_01")

    assert build.attributes["strength"] == 17
    assert build.attributes["agility"] == 14
    assert build.attributes["endurance"] == 16
    assert build.attributes["perception"] == 15
    assert set(build.attributes) == {
        "strength",
        "agility",
        "endurance",
        "intellect",
        "memory",
        "mental",
        "perception",
        "projection",
        "prediction",
    }
    assert build.attributes == EXPECTED_MANUAL_ATTRIBUTES["starter_guard_01"]
    assert build.skill_xp == {
        "skill_swords": 0.20,
        "skill_shield_mastery": 0.15,
        "skill_medium_armor": 0.10,
    }
    assert build.skill_keys == (
        "skill_swords",
        "skill_shield_mastery",
        "skill_medium_armor",
    )
    assert build.item_base_ids == (
        "sword",
        "shield",
        "jerkin",
        "leather_cap",
        "reinforced_gloves",
        "breeches",
        "linen_shirt",
        "travel_boots",
        "belt",
        "winter_cloak",
        "amulet",
    )


@pytest.mark.unit
def test_starting_imprint_selects_closest_profile_from_weights() -> None:
    build = StartingImprintService().build_for_weights(
        {
            "w_agility": 10,
            "w_perception": 8,
            "w_prediction": 7,
            "w_strength": 2,
        }
    )

    assert build.imprint_key == "starter_duelist_01"
    assert build.attributes["agility"] == 17
    assert build.attributes["strength"] == 16
    assert build.attributes["perception"] == 15
    assert "skill_light_armor" in build.skill_keys


@pytest.mark.unit
def test_starting_imprints_use_explicit_manual_attribute_profiles() -> None:
    service = StartingImprintService()

    assert set(EXPECTED_MANUAL_ATTRIBUTES) == set(STARTING_IMPRINTS)
    for imprint_key, definition in STARTING_IMPRINTS.items():
        expected = EXPECTED_MANUAL_ATTRIBUTES[imprint_key]
        build = service.build(imprint_key)

        assert dict(definition.attribute_values) == expected
        assert build.attributes == expected
        assert set(build.attributes) == set(ATTRIBUTE_KEYS)
        assert sorted(build.attributes.values()) == list(range(9, 18))


@pytest.mark.unit
def test_archery_starting_imprints_keep_core_resources_above_dump_stat() -> None:
    service = StartingImprintService()

    for imprint_key in ("starter_hunter_01", "starter_archer_01", "starter_marksman_01"):
        build = service.build(imprint_key)
        core_total = build.attributes["intellect"] + build.attributes["memory"] + build.attributes["mental"]

        assert build.attributes["intellect"] >= 12
        assert core_total >= 33


@pytest.mark.unit
def test_starting_imprints_define_complete_profiles_with_three_archery_starters() -> None:
    service = StartingImprintService()
    archery_imprints = {"starter_hunter_01", "starter_archer_01", "starter_marksman_01"}
    dual_imprints = {"starter_dual_blades_01", "starter_dual_sword_01", "starter_dual_mace_01"}

    assert len(STARTING_IMPRINTS) == 14
    for imprint_key, definition in STARTING_IMPRINTS.items():
        build = service.build(imprint_key)

        assert set(definition.primary_stats).issubset(set(build.attributes))
        assert sum(build.skill_xp.values()) == pytest.approx(0.45)
        assert "skill_parrying" not in build.skill_xp
        if imprint_key in dual_imprints:
            assert "skill_dual_wield" in build.skill_xp
        elif imprint_key not in archery_imprints:
            assert len(definition.primary_stats) >= 4
            assert len(build.skill_xp) == 3
        if imprint_key in archery_imprints:
            assert "skill_archery" in build.skill_xp
            assert any(base_id in build.item_base_ids for base_id in {"shortbow", "longbow", "composite_bow"})
            assert any(base_id.startswith("quiver_") for base_id in build.item_base_ids)
        else:
            assert "skill_archery" not in build.skill_xp
            assert not any(base_id in build.item_base_ids for base_id in {"shortbow", "longbow", "composite_bow"})


@pytest.mark.unit
def test_starting_imprints_keep_weapon_damage_attributes_role_appropriate() -> None:
    service = StartingImprintService()

    for imprint_key in STARTING_IMPRINTS:
        build = service.build(imprint_key)

        assert build.attributes["strength"] >= 15
        assert build.attributes["agility"] >= 12

    hunter = service.build("starter_hunter_01")
    archer = service.build("starter_archer_01")
    marksman = service.build("starter_marksman_01")

    assert hunter.attributes["agility"] > hunter.attributes["strength"]
    assert archer.attributes["agility"] > archer.attributes["strength"]
    assert marksman.attributes["strength"] >= marksman.attributes["agility"]
    assert marksman.attributes["endurance"] > hunter.attributes["endurance"]


@pytest.mark.unit
def test_dual_wield_starting_imprints_use_full_attribute_orders_and_weapon_budget() -> None:
    service = StartingImprintService()

    light = service.build("starter_dual_blades_01")
    assert light.primary_stats == (
        "agility",
        "strength",
        "perception",
        "prediction",
        "projection",
        "memory",
        "endurance",
        "mental",
        "intellect",
    )
    assert light.item_base_ids[:2] == ("stiletto", "stiletto")
    assert light.skill_xp == {
        "skill_fencing": 0.20,
        "skill_dual_wield": 0.15,
        "skill_light_armor": 0.10,
    }

    medium = service.build("starter_dual_sword_01")
    assert medium.primary_stats == (
        "strength",
        "agility",
        "endurance",
        "memory",
        "perception",
        "prediction",
        "mental",
        "projection",
        "intellect",
    )
    assert medium.item_base_ids[:2] == ("sword", "stiletto")
    assert medium.skill_xp == {
        "skill_swords": 0.10,
        "skill_fencing": 0.10,
        "skill_medium_armor": 0.15,
        "skill_dual_wield": 0.10,
    }

    heavy = service.build("starter_dual_mace_01")
    assert heavy.primary_stats == (
        "strength",
        "agility",
        "endurance",
        "mental",
        "memory",
        "perception",
        "prediction",
        "projection",
        "intellect",
    )
    assert heavy.item_base_ids[:2] == ("mace", "main_gauche")
    assert heavy.skill_xp == {
        "skill_macing": 0.10,
        "skill_fencing": 0.10,
        "skill_heavy_armor": 0.15,
        "skill_dual_wield": 0.10,
    }


@pytest.mark.unit
def test_archery_starting_imprints_include_expected_bow_and_quiver_pairs() -> None:
    service = StartingImprintService()

    hunter = service.build("starter_hunter_01")
    archer = service.build("starter_archer_01")
    marksman = service.build("starter_marksman_01")

    assert hunter.item_base_ids[:2] == ("shortbow", "quiver_frost")
    assert hunter.primary_stats == (
        "agility",
        "strength",
        "perception",
        "prediction",
        "endurance",
        "memory",
        "mental",
        "projection",
        "intellect",
    )
    assert hunter.skill_xp == {
        "skill_archery": 0.20,
        "skill_ranged_combat": 0.15,
        "skill_light_armor": 0.10,
    }
    assert archer.item_base_ids[:2] == ("longbow", "quiver_fire")
    assert archer.primary_stats == (
        "strength",
        "agility",
        "perception",
        "prediction",
        "endurance",
        "mental",
        "memory",
        "projection",
        "intellect",
    )
    assert archer.skill_xp == {
        "skill_archery": 0.20,
        "skill_ranged_combat": 0.15,
        "skill_light_armor": 0.10,
    }
    assert marksman.item_base_ids[:2] == ("composite_bow", "quiver_bodkin")
    assert marksman.primary_stats == (
        "strength",
        "agility",
        "perception",
        "endurance",
        "prediction",
        "mental",
        "memory",
        "projection",
        "intellect",
    )
    assert marksman.skill_xp == {
        "skill_archery": 0.20,
        "skill_medium_armor": 0.15,
        "skill_ranged_combat": 0.10,
    }


@pytest.mark.unit
def test_support_starting_imprints_are_combat_ready_before_respec() -> None:
    service = StartingImprintService()

    tactician = service.build("starter_tactician_01")
    assert tactician.primary_stats == ("strength", "agility", "perception", "prediction")
    assert tactician.skill_xp == {
        "skill_tactics": 0.15,
        "skill_swords": 0.20,
        "skill_medium_armor": 0.10,
    }
    assert tactician.item_base_ids[:2] == ("sword", "buckler")

    survivor = service.build("starter_rift_survivor_01")
    assert survivor.primary_stats == ("strength", "agility", "endurance", "perception")
    assert survivor.skill_xp == {
        "skill_polearms": 0.20,
        "skill_two_handed": 0.15,
        "skill_medium_armor": 0.10,
    }
    assert survivor.item_base_ids[0] == "halberd"


@pytest.mark.unit
def test_heavy_guard_uses_shield_block_without_support_parry_training() -> None:
    build = StartingImprintService().build("starter_heavy_guard_01")

    assert build.item_base_ids[:2] == ("mace", "kite_shield")
    assert build.skill_xp == {
        "skill_macing": 0.20,
        "skill_shield_mastery": 0.15,
        "skill_heavy_armor": 0.10,
    }


@pytest.mark.unit
def test_starting_imprint_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="Unknown starting imprint"):
        StartingImprintService().build("missing")
