from __future__ import annotations

import pytest

from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO


@pytest.mark.unit
def test_monster_clan_flavor_dto_accepts_structured_variant_contract() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "name_ru": "Стая Холодного Камня",
            "description": "Хищники держатся у старых плит и нападают из тумана.",
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
                    "appearance": "Серая шерсть покрыта каменной пылью.",
                    "detected": "Он застывает у плиты и смотрит на путника.",
                    "ambush": "Он выскакивает из тумана и бьет первым.",
                    "idle": "Он нюхает камни у старой дороги.",
                    "encounter": "Он выскакивает из тумана.",
                    "behavior": "Держит дистанцию и ищет слабое место.",
                }
            ],
        }
    )

    variant = flavor.variants_by_key["wolf_runner"]
    assert flavor.loot_culture.craft_style == "грубая переделка найденных вещей"
    assert flavor.loot_culture.salvage_sources == ["городские ворота", "разбитые двери"]
    assert variant.detected == "Он застывает у плиты и смотрит на путника."
    assert variant.ambush == "Он выскакивает из тумана и бьет первым."
    assert variant.idle == "Он нюхает камни у старой дороги."


@pytest.mark.unit
def test_monster_clan_flavor_dto_accepts_legacy_nested_variant_payload() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "name_ru": "Стая Старого Прохода",
            "description": "Волки держатся низины.",
            "variants_flavor": {
                "wolf_runner": {
                    "name": "Старый бегун",
                    "flavor": {
                        "appearance": "Тощий волк с серой шерстью.",
                        "encounter": "Волк выходит из низины.",
                        "behavior": "Он кружит у камней.",
                    },
                }
            },
        }
    )

    variant = flavor.variants_by_key["wolf_runner"]
    assert variant.name == "Старый бегун"
    assert variant.detected == "Волк выходит из низины."
    assert variant.ambush == "Волк выходит из низины."
    assert variant.idle == "Он кружит у камней."


@pytest.mark.unit
def test_monster_clan_flavor_schema_avoids_dynamic_object_keys() -> None:
    schema = MonsterClanFlavorDTO.model_json_schema()

    assert "additionalProperties" not in str(schema)


@pytest.mark.unit
def test_monster_clan_flavor_dump_keeps_loot_culture_with_variant_mapping() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "name_ru": "Банда Воротной Щепы",
            "description": "Разбойники держатся у пролома в старых воротах.",
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
                    "appearance": "Тощий бандит с коротким клинком.",
                }
            ],
        }
    )

    payload = flavor.model_dump_with_variant_mapping()

    assert payload["loot_culture"]["craft_style"] == "переделка городского лома"
    assert payload["variants_flavor"]["bandit_knife_rat"]["name"] == "Крыса с Кинжалом"
