import pytest

from src.backend.features.combat.services.view_service import CombatViewService


@pytest.mark.unit
def test_offense_stat_sheet_shows_rounded_damage_with_breakdown_tooltip() -> None:
    items = CombatViewService._offense_items(
        {
            "main_hand_damage_base": 17.175,
            "main_hand_damage_spread": 0.1032,
            "main_hand_damage_spread_raw": 0.12,
            "main_hand_weapon_power": 7.0,
            "main_hand_stat_damage_raw": 18.5,
            "main_hand_stat_damage_effective": 10.175,
            "main_hand_mastery_factor": 0.55,
        }
    )

    damage = next(item for item in items if item.key == "main_hand_damage")

    assert damage.value_text == "15 — 19"
    assert damage.tooltip == "Оружие: 7 // Статы: 10 из 19 // Владение: 55% // Разброс: 12% -> 10% // База: 17"
