import pytest

from src.backend.features.combat.dto import ActorLoadoutDTO, ActorMetaDTO, ActorRawDTO, ActorSnapshot
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine


def _actor_with_weapon(
    *,
    weapon_skill: str,
    skill_value: float,
    strength: float,
    agility: float,
    endurance: float,
    weapon_power: float,
    spread: float = 0.12,
) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(id=1, name="tester", type="player", team="a", hp=40, max_hp=40),
        raw=ActorRawDTO(
            attributes={
                "strength": {"base": strength, "source": {}, "temp": {}},
                "agility": {"base": agility, "source": {}, "temp": {}},
                "endurance": {"base": endurance, "source": {}, "temp": {}},
            },
            modifiers={
                "main_hand_damage_base": {"base": weapon_power, "source": {}, "temp": {}},
                "main_hand_damage_spread": {"base": spread, "source": {}, "temp": {}},
            },
            rules={"attribute_profile": "player"},
        ),
        skills={weapon_skill: skill_value},
        loadout=ActorLoadoutDTO(layout={"main_hand": weapon_skill}),
    )


@pytest.mark.unit
def test_stats_engine_assembles_weapon_base_from_weighted_stats_and_mastery() -> None:
    actor = _actor_with_weapon(
        weapon_skill="skill_fencing",
        skill_value=0.4,
        strength=17,
        agility=10,
        endurance=5,
        weapon_power=7,
        spread=0.12,
    )

    StatsEngine.ensure_stats(actor)

    assert actor.stats is not None
    mods = actor.stats.mods
    stat_raw = (17 * 0.5) + (10 * 1.0)
    mastery = 0.25 + (0.75 * 0.4)
    assert mods.main_hand_weapon_power == pytest.approx(7.0)
    assert mods.main_hand_stat_damage_raw == pytest.approx(stat_raw)
    assert mods.main_hand_mastery_factor == pytest.approx(mastery)
    assert mods.main_hand_stat_damage_effective == pytest.approx(stat_raw * mastery)
    assert mods.main_hand_damage_base == pytest.approx(7.0 + (stat_raw * mastery))
    assert mods.main_hand_damage_spread_raw == pytest.approx(0.12)
    assert mods.main_hand_damage_spread == pytest.approx(0.12 * (1.0 - (0.35 * 0.4)))


@pytest.mark.unit
def test_weapon_power_is_not_reduced_by_low_mastery() -> None:
    actor = _actor_with_weapon(
        weapon_skill="skill_macing",
        skill_value=0.0,
        strength=12,
        agility=8,
        endurance=6,
        weapon_power=9,
    )

    StatsEngine.ensure_stats(actor)

    assert actor.stats is not None
    mods = actor.stats.mods
    stat_raw = (12 * 1.0) + (8 * 0.2) + (6 * 0.4)
    assert mods.main_hand_weapon_power == pytest.approx(9.0)
    assert mods.main_hand_stat_damage_effective == pytest.approx(stat_raw * 0.25)
    assert mods.main_hand_damage_base == pytest.approx(9.0 + (stat_raw * 0.25))
