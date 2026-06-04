from __future__ import annotations

import pytest

from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO, MonsterVariantFlavorDTO


@pytest.mark.unit
def test_monster_clan_flavor_dto_accepts_structured_variant_contract() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "display_name": {"ru": "Стая Холодного Камня", "en": "Cold Stone Pack"},
            "description": {
                "ru": "Хищники держатся у старых плит и нападают из тумана.",
                "en": "Predators keep to the old slabs and strike from the fog.",
            },
            "visual_hint": {
                "ru": "серые силуэты, каменная пыль, низкий туман",
                "en": "gray silhouettes, stone dust, low fog",
            },
            "encounter_texts": {
                "patrol": {
                    "ru": "Стая пересекает дорогу низкой серой цепью.",
                    "en": "The pack crosses the road in a low gray line.",
                },
                "ambush": {
                    "ru": "Серые силуэты бросаются из тумана без предупреждения.",
                    "en": "Gray shapes burst from the fog without warning.",
                },
                "lair": {
                    "ru": "У старых плит стая встречает чужака плотным кольцом.",
                    "en": "By the old slabs, the pack closes around intruders.",
                },
                "random_meeting": {
                    "ru": "Из низины выходят хищники с каменной пылью на шерсти.",
                    "en": "Predators rise from the hollow with stone dust in their fur.",
                },
            },
            "loot_culture": {
                "craft_style": "грубая переделка найденных вещей",
                "craft_skill_hint": "не кузнецы; используют двери, ремни и гвозди",
                "salvage_sources": ["городские ворота", "разбитые двери"],
                "tone_hints": ["уличная практичность", "следы поспешной починки"],
                "equipment_origin_notes": ["снаряжение выглядит украденным или собранным из руин"],
            },
            "variants_flavor": [
                {
                    "variant_key": "wolf_runner",
                    "display_name": {"ru": "Каменный бегун", "en": "Stone Runner"},
                    "short_description": {
                        "ru": "Серая шерсть покрыта каменной пылью.",
                        "en": "Gray fur is coated in stone dust.",
                    },
                    "appearance": {
                        "ru": "низкий силуэт, пыль на загривке",
                        "en": "low silhouette, dust along the ruff",
                    },
                    "visual_hint": {
                        "ru": "низкий силуэт, пыль на загривке",
                        "en": "low silhouette, dust along the ruff",
                    },
                }
            ],
        }
    )

    variant = flavor.variants_by_key["wolf_runner"]
    assert flavor.loot_culture.craft_style == "грубая переделка найденных вещей"
    assert flavor.loot_culture.salvage_sources == ["городские ворота", "разбитые двери"]
    assert flavor.encounter_texts.patrol.ru == "Стая пересекает дорогу низкой серой цепью."
    assert flavor.encounter_texts.patrol.en == "The pack crosses the road in a low gray line."
    assert variant.short_description.ru == "Серая шерсть покрыта каменной пылью."
    assert variant.visual_hint.en == "low silhouette, dust along the ruff"


@pytest.mark.unit
def test_monster_clan_flavor_dto_rejects_member_encounter_prose() -> None:
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        MonsterClanFlavorDTO.model_validate(
            {
                "display_name": {"ru": "Стая Старого Прохода", "en": "Old Pass Pack"},
                "description": {"ru": "Волки держатся низины.", "en": "Wolves keep to the hollow."},
                "visual_hint": {"ru": "низина и серые волки", "en": "hollow and gray wolves"},
                "encounter_texts": {
                    "patrol": {"ru": "Стая идет вдоль старого прохода.", "en": "The pack follows the old pass."},
                    "ambush": {"ru": "Стая режет путь из низкого тумана.", "en": "The pack cuts in from low fog."},
                    "lair": {"ru": "У низины волки держат землю.", "en": "The wolves hold the hollow."},
                    "random_meeting": {
                        "ru": "Волки выходят из старого прохода.",
                        "en": "Wolves emerge from the old pass.",
                    },
                },
                "variants_flavor": [
                    {
                        "variant_key": "wolf_runner",
                        "name": "Старый бегун",
                        "short_description": "Тощий волк с серой шерстью.",
                        "encounter": "Волк выходит из низины.",
                        "detected": "Волк смотрит на путника.",
                        "ambush": "Волк бросается первым.",
                    }
                ],
            }
        )


@pytest.mark.unit
def test_monster_clan_flavor_schema_avoids_dynamic_object_keys() -> None:
    schema = MonsterClanFlavorDTO.model_json_schema()
    variant_schema = MonsterVariantFlavorDTO.model_json_schema()

    assert "additionalProperties" not in str(schema)
    assert "additional_properties" not in str(schema)
    assert "encounter_texts" in str(schema)
    assert "detected" not in str(variant_schema)
    assert "ambush" not in str(variant_schema)
    assert "idle" not in str(variant_schema)
    assert "encounter" not in str(variant_schema)


@pytest.mark.unit
def test_monster_clan_flavor_dump_keeps_loot_culture_with_variant_mapping() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "display_name": {"ru": "Банда Воротной Щепы", "en": "Gate-Splinter Gang"},
            "description": {
                "ru": "Разбойники держатся у пролома в старых воротах.",
                "en": "Bandits hold the breach in the old gate.",
            },
            "visual_hint": {
                "ru": "щитовые доски, ремни, ржавые ворота",
                "en": "shield boards, straps, rusted gate",
            },
            "encounter_texts": {
                "patrol": {"ru": "Банда идет вдоль ворот.", "en": "The gang walks along the gate."},
                "ambush": {"ru": "Банда бьет из пролома.", "en": "The gang strikes from the breach."},
                "lair": {"ru": "Банда держит пролом.", "en": "The gang holds the breach."},
                "random_meeting": {"ru": "Банда выходит у ворот.", "en": "The gang appears by the gate."},
            },
            "loot_culture": {
                "craft_style": "переделка городского лома",
                "craft_skill_hint": "чинят ремнями и гвоздями, а не кузнечной работой",
                "salvage_sources": ["обшивка ворот"],
                "tone_hints": ["небрежная сборка"],
                "equipment_origin_notes": ["щит может быть куском двери"],
            },
            "variants_flavor": [
                {
                    "variant_key": "bandit_knife_rat",
                    "display_name": {"ru": "Крыса с Кинжалом", "en": "Dagger Rat"},
                    "short_description": {
                        "ru": "Тощий бандит с коротким клинком.",
                        "en": "A gaunt bandit with a short blade.",
                    },
                    "appearance": {
                        "ru": "короткий клинок, рваная куртка",
                        "en": "short blade, torn jacket",
                    },
                    "visual_hint": {
                        "ru": "короткий клинок, рваная куртка",
                        "en": "short blade, torn jacket",
                    },
                }
            ],
        }
    )

    payload = flavor.model_dump_with_variant_mapping()

    assert payload["loot_culture"]["craft_style"] == "переделка городского лома"
    assert payload["variants_flavor"]["bandit_knife_rat"]["name"] == "Крыса с Кинжалом"
    assert payload["variants_flavor"]["bandit_knife_rat"]["display_name"]["en"] == "Dagger Rat"
    assert payload["name_ru"] == "Банда Воротной Щепы"
