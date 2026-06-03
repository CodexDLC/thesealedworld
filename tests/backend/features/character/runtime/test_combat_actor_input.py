import pytest

from src.backend.features.character.runtime import CharacterCombatActorInputBuilder
from src.backend.features.game_catalog.combat.resources.feints.availability import (
    ARCHERY_WEAPON_FEINTS,
    BASIC_ARCHERY_FEINTS,
    BASIC_FEINTS,
    DUAL_WIELD_TACTICAL_FEINTS,
    FENCING_WEAPON_FEINTS,
    MACING_WEAPON_FEINTS,
    RANGED_TACTICAL_FEINTS,
    SHIELD_TACTICAL_FEINTS,
    SWORD_WEAPON_FEINTS,
    TWO_HANDED_TACTICAL_FEINTS,
)


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
            "skill_swords": {"xp": 0.35},
            "skill_light_armor": 0.2,
            "skill_parrying": 0.25,
        },
        "symbiote": {"name": "SYSTEM", "gift_rank": 7},
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
                        "base_id": "short_sword",
                        "power": 7,
                        "material": {"id": "iron", "tier_mult": 1.2},
                        "metadata": {"tier": 1},
                        "implicit_bonuses": {"parry_chance": 0.1},
                        "triggers": ["crit.weapon_precision_crit"],
                    },
                },
                "armor-1": {
                    "item_id": "armor-1",
                    "item_type": "armor",
                    "related_skill": "skill_light_armor",
                    "mechanics": {"base_id": "leather_vest", "armor_class": "light", "power": 4, "metadata": {"tier": 2}},
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
        "skill_light_armor": 0.2,
        "skill_parrying": 0.25,
        "skill_swords": 0.35,
    }
    assert actor_input["raw"]["modifiers"]["main_hand_damage_base"]["base"] == 7.0
    assert actor_input["raw"]["modifiers"]["parry"]["base"] == 0.1
    assert actor_input["raw"]["modifiers"]["parry"]["source"] == {}
    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_swords"
    assert actor_input["loadout"]["layout"]["main_hand_trigger"] == "crit.weapon_precision_crit"
    assert actor_input["loadout"]["layout"]["body"] == "skill_light_armor"
    assert actor_input["loadout"]["combat_surfaces"]["main_hand"] == {
        "slot": "main_hand",
        "delivery": "weapon",
        "surface": "weapon",
        "tags": [],
        "item_id": "sword-1",
        "base_id": "short_sword",
        "skill_key": "skill_swords",
    }
    assert actor_input["loadout"]["equipment_layout"] == {"main_hand": "sword-1", "chest_armor": "armor-1"}
    assert actor_input["loadout"]["equipment_refs"]["main_hand"] == {
        "slot": "main_hand",
        "combat_slot": "main_hand",
        "item_id": "sword-1",
        "base_id": "short_sword",
        "item_type": "weapon",
        "material_id": "iron",
        "tier": 1,
        "combat_tier": 2,
        "tier_mult": 1.2,
        "sync_delta": 5,
        "durability_stress_mult": pytest.approx(5.0),
        "overload_penalty_mult": 1.0,
        "overdrive_bonus_factor": pytest.approx(0.25),
        "power": 7.0,
        "armor_class": None,
        "skill_key": "skill_swords",
        "triggers": ["crit.weapon_precision_crit"],
        "tags": [],
    }
    assert actor_input["loadout"]["equipment_refs"]["body"]["armor_class"] == "light"
    assert actor_input["loadout"]["equipment_refs"]["body"]["combat_tier"] == 3
    assert actor_input["loadout"]["hand_usage"] == {}
    assert actor_input["loadout"]["two_handed"] is False
    assert actor_input["loadout"]["weapon_slots"] == ["main_hand"]
    assert actor_input["loadout"]["belt"][0]["belt_slot"] == "belt_slot_1"
    assert actor_input["loadout"]["known_abilities"] == [
        "basic_punish_mistake",
        "basic_finish_moment",
        "basic_break_stance",
        "basic_expose_weakness",
        "basic_wipe_blood",
        "basic_grit_teeth",
        "basic_bloody_answer",
        "basic_last_push",
        "minor_heal",
    ]
    assert actor_input["loadout"]["known_feints"] == [*BASIC_FEINTS, *SWORD_WEAPON_FEINTS]


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
    assert snapshot["combat"]["loadout"]["known_abilities"] == [
        "basic_punish_mistake",
        "basic_finish_moment",
        "basic_break_stance",
        "basic_expose_weakness",
        "basic_wipe_blood",
        "basic_grit_teeth",
        "basic_bloody_answer",
        "basic_last_push",
    ]
    assert snapshot["combat"]["loadout"]["combat_surfaces"]["main_hand"] == {
        "slot": "main_hand",
        "delivery": "unarmed",
        "surface": "hands",
        "tags": [],
        "item_id": "",
        "base_id": "",
        "skill_key": "skill_unarmed",
    }
    assert snapshot["combat"]["loadout"]["known_feints"] == list(BASIC_FEINTS)


@pytest.mark.unit
def test_builder_overlays_pending_expedition_skill_progress() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_swords": {"xp": 0.2}},
            "pending_progress": {"skills": {"skill_swords": 0.1, "skill_parrying": 0.05}},
            "items": {},
        }
    )

    assert actor_input["skills"]["skill_swords"] == 0.3
    assert actor_input["skills"]["skill_parrying"] == 0.05


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
                            "triggers": ["crit.weapon_precision_crit"],
                        },
                    }
                },
            },
        }
    )

    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_swords"
    assert actor_input["loadout"]["layout"]["main_hand_trigger"] == "crit.weapon_precision_crit"
    assert actor_input["loadout"]["equipment_layout"] == {"two_hand": "katana-1"}
    assert actor_input["loadout"]["hand_usage"] == {"main_hand": "two_hand"}
    assert actor_input["loadout"]["two_handed"] is True
    assert actor_input["loadout"]["weapon_slots"] == []
    assert actor_input["loadout"]["layout"]["tactical_style"] == "skill_two_handed"
    assert actor_input["loadout"]["layout"]["tactical_style_trigger"] == "accuracy.style_2h_ignore"
    assert actor_input["loadout"]["known_feints"] == [*BASIC_FEINTS, *SWORD_WEAPON_FEINTS, *TWO_HANDED_TACTICAL_FEINTS]


@pytest.mark.unit
def test_builder_maps_archery_two_hand_to_ranged_combat_style() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_archery": 0.3, "skill_ranged_combat": 0.2},
            "items": {
                "layout": {"equipment": {"two_hand": "shortbow-1"}},
                "by_id": {
                    "shortbow-1": {
                        "item_id": "shortbow-1",
                        "item_type": "weapon",
                        "slot": "two_hand",
                        "mechanics": {
                            "power": 7,
                            "related_skill": "skill_archery",
                        },
                    }
                },
            },
        }
    )

    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_archery"
    assert actor_input["loadout"]["hand_usage"] == {"main_hand": "two_hand"}
    assert actor_input["loadout"]["layout"]["tactical_style"] == "skill_ranged_combat"
    assert actor_input["loadout"]["layout"]["tactical_style_trigger"] == "dodge.style_ranged_perfect_backstep"
    assert actor_input["loadout"]["known_feints"] == [
        *BASIC_ARCHERY_FEINTS,
        *ARCHERY_WEAPON_FEINTS,
        *RANGED_TACTICAL_FEINTS,
    ]


@pytest.mark.unit
def test_builder_maps_equipped_quiver_payload_to_archery_main_hand() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_archery": 0.3, "skill_ranged_combat": 0.2},
            "items": {
                "layout": {"equipment": {"two_hand": "shortbow-1", "quiver": "fire-quiver-1"}},
                "by_id": {
                    "shortbow-1": {
                        "item_id": "shortbow-1",
                        "item_type": "weapon",
                        "slot": "two_hand",
                        "mechanics": {
                            "power": 7,
                            "related_skill": "skill_archery",
                        },
                    },
                    "fire-quiver-1": {
                        "item_id": "fire-quiver-1",
                        "item_type": "ammo",
                        "slot": "quiver",
                        "mechanics": {
                            "power": 2.4,
                            "ammo_charge_base": 12,
                            "ammo_charge_skill_bonus": 12,
                            "ammo_effect_payload": {
                                "effects": [
                                    {
                                        "id": "dot_burn",
                                        "params": {"power": 1.0},
                                        "tags": ["arrow", "fire", "burn"],
                                    },
                                    {
                                        "id": "debuff_accuracy",
                                        "params": {"power": 1.0},
                                        "tags": ["arrow", "fire", "accuracy_debuff"],
                                    },
                                ]
                            },
                        },
                    },
                },
            },
        }
    )

    assert actor_input["loadout"]["ammo_effects"] == {
        "main_hand": {
            "effects": [
                {
                    "id": "dot_burn",
                    "params": {"power": 2.4},
                    "tags": ["arrow", "fire", "burn"],
                },
                {
                    "id": "debuff_accuracy",
                    "params": {"power": 2.4},
                    "tags": ["arrow", "fire", "accuracy_debuff"],
                },
            ]
        }
    }
    assert actor_input["loadout"]["ammo_charges"] == {"main_hand": 15}
    assert actor_input["loadout"]["ammo_charge_caps"] == {"main_hand": 15}


@pytest.mark.unit
def test_builder_ignores_equipped_quiver_payload_without_archery_weapon() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_swords": 0.3},
            "items": {
                "layout": {"equipment": {"main_hand": "sword-1", "quiver": "fire-quiver-1"}},
                "by_id": {
                    "sword-1": {
                        "item_id": "sword-1",
                        "item_type": "weapon",
                        "slot": "main_hand",
                        "mechanics": {
                            "power": 7,
                            "related_skill": "skill_swords",
                        },
                    },
                    "fire-quiver-1": {
                        "item_id": "fire-quiver-1",
                        "item_type": "ammo",
                        "slot": "quiver",
                        "mechanics": {
                            "ammo_effect_payload": {
                                "id": "dot_burn",
                                "params": {"power": 1.0},
                            },
                        },
                    },
                },
            },
        }
    )

    assert actor_input["loadout"]["ammo_effects"] == {}
    assert actor_input["loadout"]["ammo_charges"] == {}


@pytest.mark.unit
def test_builder_marks_only_real_offhand_weapons_for_dual_wield() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_macing": 0.2, "skill_shield_mastery": 0.25, "skill_dual_wield": 0.0},
            "items": {
                "layout": {"equipment": {"main_hand": "mace-1", "off_hand": "shield-1"}},
                "by_id": {
                    "mace-1": {
                        "item_id": "mace-1",
                        "item_type": "weapon",
                        "related_skill": "skill_macing",
                        "mechanics": {"power": 8},
                    },
                    "shield-1": {
                        "item_id": "shield-1",
                        "item_type": "armor",
                        "related_skill": "skill_shield_mastery",
                        "mechanics": {"power": 4, "tags": ["shield"]},
                    },
                },
            },
        }
    )

    assert actor_input["loadout"]["layout"]["off_hand"] == "skill_shield_mastery"
    assert actor_input["loadout"]["layout"]["tactical_style"] == "skill_shield_mastery"
    assert actor_input["loadout"]["layout"]["tactical_style_trigger"] == "block.style_shield_reflect"
    assert actor_input["loadout"]["equipment_layout"]["off_hand"] == "shield-1"
    assert actor_input["loadout"]["weapon_slots"] == ["main_hand"]
    assert actor_input["loadout"]["known_feints"] == [*BASIC_FEINTS, *MACING_WEAPON_FEINTS, *SHIELD_TACTICAL_FEINTS]


@pytest.mark.unit
def test_builder_maps_two_real_weapons_to_dual_wield_style() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_swords": 0.2, "skill_fencing": 0.2, "skill_dual_wield": 0.15},
            "items": {
                "layout": {"equipment": {"main_hand": "sword-1", "off_hand": "stiletto-1"}},
                "by_id": {
                    "sword-1": {
                        "item_id": "sword-1",
                        "item_type": "weapon",
                        "related_skill": "skill_swords",
                        "mechanics": {"power": 8},
                    },
                    "stiletto-1": {
                        "item_id": "stiletto-1",
                        "item_type": "weapon",
                        "related_skill": "skill_fencing",
                        "mechanics": {"power": 4, "tags": ["dagger", "fencing", "offhand"]},
                    },
                },
            },
        }
    )

    assert actor_input["loadout"]["layout"]["main_hand"] == "skill_swords"
    assert actor_input["loadout"]["layout"]["off_hand"] == "skill_fencing"
    assert actor_input["loadout"]["layout"]["tactical_style"] == "skill_dual_wield"
    assert actor_input["loadout"]["layout"]["tactical_style_trigger"] == "crit.style_dual_cross_cut"
    assert actor_input["loadout"]["two_handed"] is False
    assert actor_input["loadout"]["weapon_slots"] == ["main_hand", "off_hand"]
    assert actor_input["loadout"]["known_feints"] == [
        *BASIC_FEINTS,
        *SWORD_WEAPON_FEINTS,
        *FENCING_WEAPON_FEINTS,
        *DUAL_WIELD_TACTICAL_FEINTS,
    ]


@pytest.mark.unit
def test_builder_treats_buckler_as_light_shield_not_parry_weapon() -> None:
    actor_input = CharacterCombatActorInputBuilder().build_input(
        {
            "char_id": 7,
            "bio": {"name": "Ada"},
            "attributes": {},
            "skills": {"skill_swords": 0.2, "skill_shield_mastery": 0.1},
            "items": {
                "layout": {"equipment": {"main_hand": "sword-1", "off_hand": "buckler-1"}},
                "by_id": {
                    "sword-1": {
                        "item_id": "sword-1",
                        "item_type": "weapon",
                        "related_skill": "skill_swords",
                        "mechanics": {"power": 8},
                    },
                    "buckler-1": {
                        "item_id": "buckler-1",
                        "item_type": "armor",
                        "related_skill": "skill_shield_mastery",
                        "mechanics": {"power": 3, "tags": ["buckler", "shield", "small_shield"]},
                    },
                },
            },
        }
    )

    assert actor_input["loadout"]["layout"]["off_hand"] == "skill_shield_mastery"
    assert actor_input["loadout"]["layout"]["tactical_style"] == "skill_shield_mastery"
    assert actor_input["loadout"]["equipment_layout"]["off_hand"] == "buckler-1"
    assert actor_input["loadout"]["known_feints"] == [*BASIC_FEINTS, *SWORD_WEAPON_FEINTS, *SHIELD_TACTICAL_FEINTS]


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
    assert actor_input["raw"]["modifiers"]["main_hand_accuracy"]["base"] == 0.0
    assert actor_input["raw"]["modifiers"]["main_hand_damage_base"]["base"] == 12.0
    assert actor_input["loadout"]["known_feints"] == list(BASIC_FEINTS)
