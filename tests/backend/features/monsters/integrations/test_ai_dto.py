from __future__ import annotations

import pytest

from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO


@pytest.mark.unit
def test_monster_clan_flavor_dto_accepts_structured_variant_contract() -> None:
    flavor = MonsterClanFlavorDTO.model_validate(
        {
            "name_ru": "Стая Холодного Камня",
            "description": "Хищники держатся у старых плит и нападают из тумана.",
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
