from __future__ import annotations

import pytest

from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO, MonsterVariantFlavorDTO


@pytest.mark.unit
def test_monster_clan_flavor_dto_accepts_structured_variant_contract() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "name_ru": "Стая Холодного Камня",
            "description": "Хищники держатся у старых плит и нападают из тумана.",
            "encounter_texts": {
                "patrol": "Стая пересекает дорогу низкой серой цепью.",
                "ambush": "Серые силуэты бросаются из тумана без предупреждения.",
                "lair": "У старых плит стая встречает чужака плотным кольцом.",
                "random_meeting": "Из низины выходят хищники с каменной пылью на шерсти.",
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
                    "name": "Каменный бегун",
                    "short_description": "Серая шерсть покрыта каменной пылью.",
                    "visual_hint": "низкий силуэт, пыль на загривке",
                }
            ],
        }
    )

    variant = flavor.variants_by_key["wolf_runner"]
    assert flavor.loot_culture.craft_style == "грубая переделка найденных вещей"
    assert flavor.loot_culture.salvage_sources == ["городские ворота", "разбитые двери"]
    assert flavor.encounter_texts.patrol == "Стая пересекает дорогу низкой серой цепью."
    assert variant.short_description == "Серая шерсть покрыта каменной пылью."
    assert variant.visual_hint == "низкий силуэт, пыль на загривке"


@pytest.mark.unit
def test_monster_clan_flavor_dto_rejects_member_encounter_prose() -> None:
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        MonsterClanFlavorDTO.model_validate(
            {
                "name_ru": "Стая Старого Прохода",
                "description": "Волки держатся низины.",
                "encounter_texts": {
                    "patrol": "Стая идет вдоль старого прохода.",
                    "ambush": "Стая режет путь из низкого тумана.",
                    "lair": "У низины волки держат землю.",
                    "random_meeting": "Волки выходят из старого прохода.",
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
    assert "encounter_texts" in str(schema)
    assert "detected" not in str(variant_schema)
    assert "ambush" not in str(variant_schema)
    assert "idle" not in str(variant_schema)
    assert "encounter" not in str(variant_schema)


@pytest.mark.unit
def test_monster_clan_flavor_dump_keeps_loot_culture_with_variant_mapping() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "name_ru": "Банда Воротной Щепы",
            "description": "Разбойники держатся у пролома в старых воротах.",
            "encounter_texts": {
                "patrol": "Банда идет вдоль ворот.",
                "ambush": "Банда бьет из пролома.",
                "lair": "Банда держит пролом.",
                "random_meeting": "Банда выходит у ворот.",
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
                    "name": "Крыса с Кинжалом",
                    "short_description": "Тощий бандит с коротким клинком.",
                }
            ],
        }
    )

    payload = flavor.model_dump_with_variant_mapping()

    assert payload["loot_culture"]["craft_style"] == "переделка городского лома"
    assert payload["variants_flavor"]["bandit_knife_rat"]["name"] == "Крыса с Кинжалом"
