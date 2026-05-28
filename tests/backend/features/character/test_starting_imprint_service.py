import pytest

from src.backend.features.character.resources import STARTING_IMPRINTS
from src.backend.features.character.services import StartingImprintService


@pytest.mark.unit
def test_starting_imprint_builds_complete_guard_payload() -> None:
    build = StartingImprintService().build("starter_guard_01")

    assert build.attributes["endurance"] == 17
    assert build.attributes["strength"] == 16
    assert build.attributes["perception"] == 15
    assert build.attributes["mental"] == 14
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
    assert sorted(build.attributes[stat] for stat in set(build.attributes) - set(build.primary_stats)) == [
        9,
        10,
        11,
        12,
        13,
    ]
    assert build.skill_xp == {
        "skill_swords": 0.15,
        "skill_shield_mastery": 0.15,
        "skill_parrying": 0.10,
        "skill_medium_armor": 0.10,
    }
    assert build.skill_keys == (
        "skill_swords",
        "skill_shield_mastery",
        "skill_parrying",
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
    assert build.attributes["perception"] == 16
    assert "skill_light_armor" in build.skill_keys


@pytest.mark.unit
def test_starting_imprints_define_eleven_four_skill_profiles_with_two_archery_starters() -> None:
    service = StartingImprintService()
    archery_imprints = {"starter_hunter_01", "starter_archer_01"}

    assert len(STARTING_IMPRINTS) == 11
    for imprint_key, definition in STARTING_IMPRINTS.items():
        build = service.build(imprint_key)

        assert len(definition.primary_stats) == 4
        assert len(build.skill_xp) == 4
        assert sorted(build.skill_xp.values()) == [0.10, 0.10, 0.15, 0.15]
        if imprint_key in archery_imprints:
            assert "skill_archery" in build.skill_xp
            assert any(base_id in build.item_base_ids for base_id in {"shortbow", "longbow"})
            assert any(base_id.startswith("quiver_") for base_id in build.item_base_ids)
        else:
            assert "skill_archery" not in build.skill_xp
            assert not any(base_id in build.item_base_ids for base_id in {"shortbow", "longbow"})


@pytest.mark.unit
def test_archery_starting_imprints_include_expected_bow_and_quiver_pairs() -> None:
    service = StartingImprintService()

    hunter = service.build("starter_hunter_01")
    archer = service.build("starter_archer_01")

    assert hunter.item_base_ids[:2] == ("shortbow", "quiver_poison")
    assert hunter.skill_xp == {
        "skill_archery": 0.15,
        "skill_scouting": 0.15,
        "skill_pathfinder": 0.10,
        "skill_light_armor": 0.10,
    }
    assert archer.item_base_ids[:2] == ("longbow", "quiver_training")
    assert archer.skill_xp == {
        "skill_archery": 0.15,
        "skill_ranged_combat": 0.15,
        "skill_tactics": 0.10,
        "skill_light_armor": 0.10,
    }


@pytest.mark.unit
def test_starting_imprint_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="Unknown starting imprint"):
        StartingImprintService().build("missing")
