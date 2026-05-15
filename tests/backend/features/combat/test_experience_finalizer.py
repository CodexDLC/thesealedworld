import pytest

from src.backend.features.combat.dto import (
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.runtime.engine.mechanics_service import MechanicsService
from src.backend.features.combat.runtime.services.experience_finalizer import CombatExperienceFinalizer


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
        "loadout": {"layout": {"main_hand": "skill_swords"}},
        "skills": {"skill_swords": 0.0, "skill_parrying": 0.0},
        "xp_buffer": {
            "main_hand_hit": 2,
            "main_hand_miss": 1,
            "main_hand_crit": 1,
            "defense_parry": 1,
            "kill_generic": 1,
        },
    }

    rewards = CombatExperienceFinalizer().calculate_actor_rewards(actor)

    assert rewards == {
        "skill_swords": 0.0048,
        "skill_parrying": 0.0016,
        "free_xp": 0.0016,
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

    assert rewards == {"free_xp": 0.0012}


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

    assert results["7"].rewards == {"free_xp": 0.0012}
    assert recorder.calls == [(7, {"free_xp": 0.0012})]
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
