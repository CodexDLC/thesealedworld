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
    extra_modifiers: dict[str, float] | None = None,
    extra_skills: dict[str, float] | None = None,
    extra_layout: dict[str, str] | None = None,
) -> ActorSnapshot:
    modifiers = {
        "main_hand_damage_base": {"base": weapon_power, "source": {}, "temp": {}},
        "main_hand_damage_spread": {"base": spread, "source": {}, "temp": {}},
    }
    for key, value in (extra_modifiers or {}).items():
        modifiers[key] = {"base": value, "source": {}, "temp": {}}
    skills = {weapon_skill: skill_value, **(extra_skills or {})}
    layout = {"main_hand": weapon_skill, **(extra_layout or {})}
    return ActorSnapshot(
        meta=ActorMetaDTO(id=1, name="tester", type="player", team="a", hp=40, max_hp=40),
        raw=ActorRawDTO(
            attributes={
                "strength": {"base": strength, "source": {}, "temp": {}},
                "agility": {"base": agility, "source": {}, "temp": {}},
                "endurance": {"base": endurance, "source": {}, "temp": {}},
            },
            modifiers=modifiers,
            rules={"attribute_profile": "player"},
        ),
        skills=skills,
        loadout=ActorLoadoutDTO(layout=layout),
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
    stat_raw = (17 * 0.20) + (10 * 0.70) + (5 * 0.10)
    mastery = 0.25 + (0.75 * 0.4)
    assert mods.main_hand_weapon_power == pytest.approx(7.0)
    assert mods.main_hand_stat_damage_raw == pytest.approx(stat_raw)
    assert mods.main_hand_mastery_factor == pytest.approx(mastery)
    assert mods.main_hand_stat_damage_effective == pytest.approx(stat_raw * mastery)
    assert mods.main_hand_damage_base == pytest.approx(7.0 + (stat_raw * mastery))
    assert mods.main_hand_damage_spread_raw == pytest.approx(0.12)
    assert mods.main_hand_damage_spread == pytest.approx(0.12 * (1.0 - (0.50 * 0.4)))


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
    stat_raw = (12 * 0.60) + (8 * 0.10) + (6 * 0.30)
    assert mods.main_hand_weapon_power == pytest.approx(9.0)
    assert mods.main_hand_stat_damage_effective == pytest.approx(stat_raw * 0.25)
    assert mods.main_hand_damage_base == pytest.approx(9.0 + (stat_raw * 0.25))


@pytest.mark.unit
def test_weapon_damage_uses_endurance_as_normalized_body_weight_for_macing() -> None:
    low_endurance = _actor_with_weapon(
        weapon_skill="skill_macing",
        skill_value=0.5,
        strength=16,
        agility=12,
        endurance=4,
        weapon_power=13,
    )
    high_endurance = _actor_with_weapon(
        weapon_skill="skill_macing",
        skill_value=0.5,
        strength=16,
        agility=12,
        endurance=24,
        weapon_power=13,
    )

    StatsEngine.ensure_stats(low_endurance)
    StatsEngine.ensure_stats(high_endurance)

    assert low_endurance.stats is not None
    assert high_endurance.stats is not None
    low_stat_raw = (16 * 0.60) + (12 * 0.10) + (4 * 0.30)
    high_stat_raw = (16 * 0.60) + (12 * 0.10) + (24 * 0.30)
    mastery = 0.25 + (0.75 * 0.5)
    assert low_endurance.stats.mods.main_hand_stat_damage_raw == pytest.approx(low_stat_raw)
    assert high_endurance.stats.mods.main_hand_stat_damage_raw == pytest.approx(high_stat_raw)
    assert low_endurance.stats.mods.main_hand_damage_base == pytest.approx(13 + (low_stat_raw * mastery))
    assert high_endurance.stats.mods.main_hand_damage_base == pytest.approx(13 + (high_stat_raw * mastery))
    assert high_endurance.stats.mods.main_hand_damage_base > low_endurance.stats.mods.main_hand_damage_base


@pytest.mark.unit
def test_shield_style_adds_endurance_guard_power_and_weapon_endurance_damage() -> None:
    actor = _actor_with_weapon(
        weapon_skill="skill_swords",
        skill_value=0.5,
        strength=10,
        agility=14,
        endurance=20,
        weapon_power=7,
        extra_modifiers={"shield_guard_power": 6.0},
        extra_skills={"skill_shield_mastery": 0.5},
        extra_layout={
            "off_hand": "skill_shield_mastery",
            "tactical_style": "skill_shield_mastery",
        },
    )

    StatsEngine.ensure_stats(actor)

    assert actor.stats is not None
    stat_raw = (10 * 0.45) + (14 * 0.35) + (20 * 0.20)
    mastery = 0.25 + (0.75 * 0.5)
    shield_style_raw = (20 * 0.60) + (10 * 0.40)
    shield_style_bonus = shield_style_raw * 0.35
    assert actor.stats.mods.main_hand_damage_base == pytest.approx(7 + (stat_raw * mastery))
    assert actor.stats.mods.shield_style_guard_power_raw == pytest.approx(shield_style_raw)
    assert actor.stats.mods.shield_style_guard_power_bonus == pytest.approx(shield_style_bonus)
    assert actor.stats.mods.shield_guard_power == pytest.approx(6 + shield_style_bonus)
