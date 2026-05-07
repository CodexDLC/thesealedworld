import pytest

from src.backend.features.character.runtime import CharacterCombatActorInputBuilder


@pytest.mark.unit
def test_builder_creates_combat_actor_input_from_active_character_document() -> None:
    ac = {
        "char_id": 7,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "bio": {"name": "Ada", "gender": "female", "avatar": "/avatar.png"},
        "location": {"current": "52_58"},
        "vitals": {"hp": {"cur": 64, "max": 64}, "energy": {"cur": 26, "max": 26}},
        "attributes": {"strength": 15, "agility": 12},
        "skills": {
            "skill_swords": {"xp": 35},
            "skill_light_armor": 20,
            "skill_parrying": 25,
        },
        "symbiote": {"name": "SYSTEM"},
        "items": {
            "layout": {
                "equipment": {
                    "main_hand": "sword-1",
                    "chest_armor": "armor-1",
                },
                "belt": {"belt_slot_1": "potion-1"},
            },
            "by_id": {
                "sword-1": {
                    "item_id": "sword-1",
                    "item_type": "weapon",
                    "related_skill": "skill_swords",
                    "mechanics": {
                        "power": 7,
                        "implicit_bonuses": {"parry_chance": 0.1},
                        "triggers": ["crit.bleed_on_crit"],
                    },
                },
                "armor-1": {
                    "item_id": "armor-1",
                    "item_type": "armor",
                    "related_skill": "skill_light_armor",
                    "mechanics": {"power": 4},
                },
                "potion-1": {
                    "item_id": "potion-1",
                    "item_type": "consumable",
                    "mechanics": {"abilities": ["minor_heal"]},
                },
            },
        },
    }

    actor_input = CharacterCombatActorInputBuilder().build_input(ac)

    assert actor_input["meta"]["actor_id"] == 7
    assert actor_input["meta"]["name"] == "Ada"
    assert actor_input["source"]["location_id"] == "52_58"
    assert actor_input["status"]["hp"]["max"] == 64
    assert actor_input["skills"] == {
        "skill_light_armor": 20.0,
        "skill_parrying": 25.0,
        "skill_swords": 35.0,
    }
    assert actor_input["raw"]["modifiers"]["main_hand_damage_base"]["base"] == 7.0
    assert actor_input["raw"]["modifiers"]["parry"]["source"]["skill:skill_parrying:item:sword-1"] == 0.1
    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_swords"
    assert actor_input["loadout"]["layout"]["main_hand_trigger"] == "crit.bleed_on_crit"
    assert actor_input["loadout"]["layout"]["body"] == "skill_light_armor"
    assert actor_input["loadout"]["equipment_layout"] == {"main_hand": "sword-1", "chest_armor": "armor-1"}
    assert actor_input["loadout"]["hand_usage"] == {}
    assert actor_input["loadout"]["two_handed"] is False
    assert actor_input["loadout"]["belt"][0]["belt_slot"] == "belt_slot_1"
    assert actor_input["loadout"]["known_abilities"] == ["minor_heal"]


@pytest.mark.unit
def test_builder_can_emit_lifecycle_compatible_snapshot() -> None:
    snapshot = CharacterCombatActorInputBuilder().build_snapshot(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "vitals": {"hp": {"cur": 10, "max": 20}},
            "attributes": {},
            "skills": {},
            "items": {},
        }
    )

    assert "attributes" in snapshot["combat"]["math_model"]
    assert snapshot["combat"]["skills"] == {}
    assert snapshot["combat"]["loadout"]["layout"] == {"main_hand": "skill_unarmed"}


@pytest.mark.unit
def test_builder_maps_two_hand_rewards_to_main_hand_combat_layout() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_swords": {"xp": 10}},
            "items": {
                "layout": {"equipment": {"two_hand": "katana-1"}},
                "by_id": {
                    "katana-1": {
                        "item_id": "katana-1",
                        "item_type": "weapon",
                        "slot": "two_hand",
                        "mechanics": {
                            "power": 9,
                            "damage_spread": 0.1,
                            "related_skill": "skill_swords",
                            "triggers": ["crit.bleed_on_crit"],
                        },
                    }
                },
            },
        }
    )

    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_swords"
    assert actor_input["loadout"]["layout"]["main_hand_trigger"] == "crit.bleed_on_crit"
    assert actor_input["loadout"]["equipment_layout"] == {"two_hand": "katana-1"}
    assert actor_input["loadout"]["hand_usage"] == {"main_hand": "two_hand"}
    assert actor_input["loadout"]["two_handed"] is True


@pytest.mark.unit
def test_builder_maps_empty_hands_to_unarmed_layout() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {"strength": 12},
            "skills": {"skill_unarmed": {"xp": 5}},
            "items": {"layout": {"equipment": {}}, "by_id": {}},
        }
    )

    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_unarmed"
    assert actor_input["raw"]["modifiers"]["main_hand_accuracy"]["base"] == 0.7
    assert actor_input["raw"]["modifiers"]["main_hand_damage_base"]["base"] == 12.0
