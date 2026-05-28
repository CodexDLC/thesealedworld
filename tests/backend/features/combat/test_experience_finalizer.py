import pytest

from src.backend.core.calculators.skill_progression_calculator import (
    SkillProgressionBatchInput,
    SkillProgressionCalculator,
    SkillProgressionEntry,
)
from src.backend.features.combat.dto import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.runtime.engine.mechanics_service import MechanicsService
from src.backend.features.combat.runtime.services.experience_finalizer import CombatExperienceFinalizer
from src.backend.features.game_catalog.skills.services import SkillCatalogService

MINIMAL_COMBAT_ATTRIBUTES = {"strength": 8, "agility": 8, "endurance": 8}


class FakeCombatDataService:
    async def get_meta(self, session_id: str):
        return {"actor_ids": ["7"]}

    def actor_ids_from_meta(self, meta):
        return ["7"]

    async def get_actors_batch(self, session_id: str, actor_ids: list[str]):
        return {
            "7": {
                "raw": {"attributes": {"strength": {"base": 8}, "agility": {"base": 8}, "endurance": {"base": 8}}},
                "loadout": {"layout": {}},
                "skills": {},
                "xp_buffer": {"free_xp": 1},
            }
        }


class FakeProgressionRecorder:
    def __init__(self) -> None:
        self.calls = []

    async def apply_progress(self, char_id: int, rewards: dict[str, float]) -> bool:
        self.calls.append((char_id, rewards))
        return True


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.calls = []

    async def apply_skill_progress(self, char_id: int, rewards: dict[str, float]) -> None:
        self.calls.append((char_id, rewards))


def _expected_skill_reward(
    skill_key: str,
    *,
    action_power: float,
    attributes: dict[str, float] | None = None,
) -> dict[str, float]:
    skill = SkillCatalogService().get(skill_key)
    assert skill is not None
    return SkillProgressionCalculator.calculate(
        SkillProgressionBatchInput(
            entries={
                skill_key: SkillProgressionEntry(
                    skill=skill,
                    attributes=attributes or _base_attributes(),
                    current_skill=0.0,
                    action_power=action_power,
                )
            }
        )
    )


def _expected_free_reward(
    *,
    action_power: float,
    attributes: dict[str, float] | None = None,
) -> dict[str, float]:
    attrs = attributes or _base_attributes()
    combat_skills = [skill for skill in SkillCatalogService().skills if skill.category.value == "combat"]
    base_power = sum(
        sum(float(attrs.get(stat_key, 0.0)) * float(weight) for stat_key, weight in skill.stat_weights.items())
        for skill in combat_skills
    ) / len(combat_skills)
    return SkillProgressionCalculator.calculate(
        SkillProgressionBatchInput(
            entries={
                "free_xp": SkillProgressionEntry(
                    attributes=attrs,
                    current_skill=0.0,
                    action_power=action_power,
                    base_power=base_power,
                    rate_mod=1.0,
                    wall_mod=0.0,
                )
            }
        )
    )


def _base_attributes(value: float = 8.0) -> dict[str, float]:
    return {
        "strength": value,
        "agility": value,
        "endurance": value,
        "perception": value,
        "intellect": value,
        "memory": value,
        "mental": value,
        "projection": value,
        "prediction": value,
    }


@pytest.mark.unit
def test_experience_finalizer_maps_flat_xp_buffer_to_skill_rewards() -> None:
    actor = {
        "raw": {
            "attributes": {
                "strength": {"base": 8},
                "agility": {"base": 8},
                "endurance": {"base": 8},
                "perception": {"base": 8},
                "intellect": {"base": 8},
                "memory": {"base": 8},
                "mental": {"base": 8},
                "projection": {"base": 8},
                "prediction": {"base": 8},
            }
        },
        "loadout": {
            "layout": {
                "main_hand": "skill_swords",
                "body": "skill_heavy_armor",
                "tactical_style": "skill_two_handed",
            }
        },
        "skills": {
            "skill_swords": 0.0,
            "skill_two_handed": 0.0,
            "skill_heavy_armor": 0.0,
            "skill_parrying": 0.0,
            "skill_anatomy": 0.0,
            "skill_tactics": 0.0,
        },
        "xp_buffer": {
            "main_hand_hit": 2,
            "main_hand_miss": 1,
            "main_hand_crit": 1,
            "defense_parry": 1,
            "defense_armor": 2,
            "kill_generic": 1,
        },
    }

    rewards = CombatExperienceFinalizer().calculate_actor_rewards(actor)

    assert rewards == {
        "skill_swords": 0.0048,
        "skill_two_handed": 0.0024,
        "skill_heavy_armor": 0.0032,
        "skill_parrying": 0.0016,
        "skill_anatomy": 0.0022,
        "skill_tactics": 0.004,
    }


@pytest.mark.unit
def test_experience_finalizer_sends_unknown_useful_actions_to_free_xp() -> None:
    actor = {
        "raw": {"attributes": {"strength": {"base": 8}, "agility": {"base": 8}, "endurance": {"base": 8}}},
        "loadout": {"layout": {}},
        "skills": {},
        "xp_buffer": {"main_hand_hit": 1},
    }

    rewards = CombatExperienceFinalizer().calculate_actor_rewards(actor)

    assert rewards == _expected_free_reward(action_power=1, attributes=MINIMAL_COMBAT_ATTRIBUTES)


@pytest.mark.unit
def test_experience_finalizer_does_not_unlock_non_combat_skills_from_combat() -> None:
    actor = {
        "raw": {"attributes": {"strength": {"base": 8}, "agility": {"base": 8}, "endurance": {"base": 8}}},
        "loadout": {"layout": {"main_hand": "skill_scouting"}},
        "skills": {},
        "xp_buffer": {"main_hand_hit": 1},
    }

    rewards = CombatExperienceFinalizer().calculate_actor_rewards(actor)

    assert rewards == _expected_free_reward(action_power=1, attributes=MINIMAL_COMBAT_ATTRIBUTES)
    assert "skill_scouting" not in rewards


@pytest.mark.unit
def test_experience_finalizer_routes_block_to_shield_mastery_even_when_skill_was_not_present() -> None:
    actor = {
        "raw": {
            "attributes": {
                "strength": {"base": 8},
                "agility": {"base": 8},
                "endurance": {"base": 8},
            }
        },
        "loadout": {"layout": {"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"}},
        "skills": {},
        "xp_buffer": {"defense_block": 1},
    }

    rewards = CombatExperienceFinalizer().calculate_actor_rewards(actor)

    assert rewards == _expected_skill_reward(
        "skill_shield_mastery",
        action_power=1,
        attributes=MINIMAL_COMBAT_ATTRIBUTES,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_experience_finalizer_routes_rewards_to_dirty_progression_recorder() -> None:
    recorder = FakeProgressionRecorder()
    sessions = FakeCharacterSessions()

    results = await CombatExperienceFinalizer().finalize(
        FakeCombatDataService(),
        "combat-1",
        "team_a",
        character_sessions=sessions,
        progression_recorder=recorder,
    )

    expected = _expected_free_reward(action_power=1, attributes=MINIMAL_COMBAT_ATTRIBUTES)
    assert results["7"].rewards == expected
    assert recorder.calls == [(7, expected)]
    assert sessions.calls == []


@pytest.mark.unit
def test_mechanics_service_records_flat_source_aware_xp_counters() -> None:
    source = ActorSnapshot(
        meta=ActorMetaDTO(id=1, name="Hero", type="player", team="a", hp=10, max_hp=10),
        raw=ActorRawDTO(),
    )
    target = ActorSnapshot(
        meta=ActorMetaDTO(id=2, name="Target", type="monster", team="b", hp=10, max_hp=10),
        raw=ActorRawDTO(),
    )
    result = InteractionResultDTO(source_id=1, target_id=2, hand="off_hand", is_hit=True, is_crit=True)

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert source.xp_buffer["off_hand_hit"] == 1.0
    assert source.xp_buffer["off_hand_crit"] == 1.0
    assert "action_hit" not in source.xp_buffer


@pytest.mark.unit
def test_mechanics_service_records_body_armor_xp_counter_for_landed_damage() -> None:
    source = ActorSnapshot(
        meta=ActorMetaDTO(id=1, name="Attacker", type="monster", team="b", hp=10, max_hp=10),
        raw=ActorRawDTO(),
    )
    target = ActorSnapshot(
        meta=ActorMetaDTO(id=2, name="Hero", type="player", team="a", hp=10, max_hp=10),
        raw=ActorRawDTO(),
        loadout=ActorLoadoutDTO(layout={"body": "skill_heavy_armor"}),
    )
    result = InteractionResultDTO(
        source_id=1,
        target_id=2,
        hand="main_hand",
        is_hit=True,
        damage_raw=7,
        damage_mitigated=3,
        damage_final=4,
    )

    MechanicsService().apply_interaction_result(PipelineContextDTO(), source, target, result)

    assert target.xp_buffer["defense_armor"] == 1.0
