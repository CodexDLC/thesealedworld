# tests/backend/features/exploration/test_encounter.py
from unittest.mock import AsyncMock

import pytest

from src.backend.features.exploration.runtime.encounter import EncounterEngine
from src.backend.features.exploration.runtime.encounter.policy import EncounterPolicy
from src.backend.features.monsters.dto import MonsterGroupMemberPreview, MonsterGroupResult
from src.shared.schemas.exploration import DetectionStatus, EncounterType


def test_encounter_chance_uses_hunting_and_pathfinder_roles():
    assert EncounterPolicy.encounter_chance(
        base_chance=0.45,
        trigger="move",
        hunting_skill=0.8,
        pathfinder_skill=0.2,
    ) == pytest.approx(0.60)
    assert EncounterPolicy.encounter_chance(
        base_chance=0.45,
        trigger="move",
        hunting_skill=0.2,
        pathfinder_skill=0.8,
    ) == pytest.approx(0.30)
    assert EncounterPolicy.encounter_chance(
        base_chance=0.80,
        trigger="search",
        scouting_skill=0.5,
        hunting_skill=0.5,
    ) == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_encounter_safe_zone():
    engine = EncounterEngine()
    location_data = {"flags": {"is_safe_zone": True}}

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data=location_data,
        scouting_skill=10.0
    )

    assert encounter is None


@pytest.mark.asyncio
async def test_encounter_city_shield_does_not_make_unsafe_ruins_safe(mocker):
    policy = EncounterPolicy()
    mocker.patch.object(policy, "should_roll", return_value=True)
    mocker.patch.object(policy, "roll", return_value=type(
        "Roll",
        (),
        {
            "discovery_type": "monster",
            "difficulty": "easy",
            "status": DetectionStatus.DETECTED,
        },
    )())
    engine = EncounterEngine(policy=policy)
    location_data = {
        "anchor_influence": {"is_inside_city_shield": True},
        "flags": {
            "is_safe_zone": False,
            "threat_tier": 1,
        }
    }
    integration = FakeEncounterIntegration()

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data=location_data,
        scouting_skill=0.0,
        trigger="move",
        loc_id="48_56",
        gear_score=100,
        encounter_integration=integration,
    )

    assert encounter is not None
    assert encounter.type == EncounterType.COMBAT
    assert encounter.metadata["kind"] == "monster_group"

@pytest.mark.asyncio
async def test_encounter_combat_generation():
    policy = EncounterPolicy()
    policy.should_roll = lambda **_: True  # type: ignore[method-assign]
    policy.roll = lambda **_: type(  # type: ignore[method-assign]
        "Roll",
        (),
        {
            "discovery_type": "monster",
            "difficulty": "mid",
            "status": DetectionStatus.DETECTED,
        },
    )()
    engine = EncounterEngine(policy=policy)
    integration = FakeEncounterIntegration()

    location_data = {"flags": {"is_safe_zone": False, "threat_tier": 1}}

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data=location_data,
        scouting_skill=100.0, # High skill for DETECTED status
        loc_id="50_50",
        gear_score=100,
        hunting_skill=1.0,
        encounter_integration=integration,
    )

    assert encounter is not None
    assert encounter.type == EncounterType.COMBAT
    assert encounter.session_id == "combat-monster-test"
    assert encounter.status == DetectionStatus.DETECTED
    assert encounter.description == "Rat scout spots you from the rubble."
    assert len(encounter.enemies) == 2
    assert encounter.enemies[0].level == 1
    assert encounter.enemies[0].member_tier == 1
    assert encounter.enemies[0].threat_rating == 3
    assert encounter.enemies[0].image == "/static/generated-assets/monsters/generated/members/rat-scout.webp"
    assert integration.prepare_monster_group.await_count == 1
    assert integration.request_combat_session.await_count == 1


@pytest.mark.asyncio
async def test_encounter_masks_monster_preview_when_hunting_is_low():
    policy = EncounterPolicy()
    policy.should_roll = lambda **_: True  # type: ignore[method-assign]
    policy.roll = lambda **_: type(  # type: ignore[method-assign]
        "Roll",
        (),
        {
            "discovery_type": "monster",
            "difficulty": "mid",
            "status": DetectionStatus.DETECTED,
        },
    )()
    engine = EncounterEngine(policy=policy)
    integration = FakeEncounterIntegration()

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data={"flags": {"is_safe_zone": False, "threat_tier": 1}},
        scouting_skill=100.0,
        loc_id="50_50",
        gear_score=100,
        hunting_skill=0.0,
        encounter_integration=integration,
    )

    assert encounter is not None
    assert encounter.info_level == 0
    assert encounter.metadata["intel"] == {"skill_key": "skill_hunting", "level": 0, "value": 0.0}
    assert encounter.enemies[0].name == "???"
    assert encounter.enemies[0].member_tier is None
    assert encounter.enemies[0].threat_rating is None
    assert encounter.enemies[0].hp_percent is None


@pytest.mark.asyncio
async def test_encounter_uses_full_player_gear_score_as_monster_budget():
    policy = EncounterPolicy()
    policy.should_roll = lambda **_: True  # type: ignore[method-assign]
    policy.roll = lambda **_: type(  # type: ignore[method-assign]
        "Roll",
        (),
        {
            "discovery_type": "monster",
            "difficulty": "mid",
            "status": DetectionStatus.DETECTED,
        },
    )()
    engine = EncounterEngine(policy=policy)
    integration = FakeEncounterIntegration()

    await engine.try_generate_encounter(
        char_id=1,
        location_data={"flags": {"is_safe_zone": False, "threat_tier": 1}},
        scouting_skill=100.0,
        loc_id="50_50",
        gear_score=506,
        encounter_integration=integration,
    )

    assert integration.prepare_monster_group.await_args.args[1] == 506


@pytest.mark.asyncio
async def test_encounter_ambush_uses_monster_ambush_text():
    policy = EncounterPolicy()
    policy.should_roll = lambda **_: True  # type: ignore[method-assign]
    policy.roll = lambda **_: type(  # type: ignore[method-assign]
        "Roll",
        (),
        {
            "discovery_type": "monster",
            "difficulty": "mid",
            "status": DetectionStatus.AMBUSH,
        },
    )()
    engine = EncounterEngine(policy=policy)
    integration = FakeEncounterIntegration()

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data={"flags": {"is_safe_zone": False, "threat_tier": 1}},
        scouting_skill=0.0,
        loc_id="50_50",
        gear_score=100,
        encounter_integration=integration,
    )

    assert encounter is not None
    assert encounter.description == "Rat scout bursts out before you can settle your stance."


class FakeEncounterIntegration:
    def __init__(self) -> None:
        self.prepare_monster_group = AsyncMock(return_value=_monster_group())
        self.request_combat_session = AsyncMock(
            return_value={
                "status": "ready",
                "combat_id": "combat-monster-test",
            }
        )


def _monster_group() -> MonsterGroupResult:
    return MonsterGroupResult(
        group_id="monster-test",
        clan_id="clan-1",
        family_id="rats",
        loc_id="50_50",
        biome_id="wasteland",
        tier=1,
        danger=0.2,
        target_budget=10,
        adjusted_budget=10,
        total_power=8,
        monster_ids=["m1", "m2"],
        actor_commitments={
            "monster:m1": "commitment-m1",
            "monster:m2": "commitment-m2",
        },
        previews=[
            MonsterGroupMemberPreview(
                monster_id="m1",
                name="Rat scout",
                description="Small but alert.",
                detected_ru="Rat scout spots you from the rubble.",
                ambush_ru="Rat scout bursts out before you can settle your stance.",
                idle_ru="Rat scout watches the passage.",
                role="scout",
                variant_key="rat_scout",
                member_tier=1,
                threat_rating=3,
                hp={"current": 12, "max": 12},
                image="/static/generated-assets/monsters/generated/members/rat-scout.webp",
                visual={"image_url": "/static/generated-assets/monsters/generated/members/rat-scout.webp"},
            ),
            MonsterGroupMemberPreview(
                monster_id="m2",
                name="Rat bruiser",
                description="Larger and meaner.",
                role="bruiser",
                variant_key="rat_bruiser",
                member_tier=1,
                threat_rating=5,
                hp={"current": 20, "max": 20},
            ),
        ],
        reused_existing_clan=True,
        context_hash="context",
        unique_hash="unique",
    )
