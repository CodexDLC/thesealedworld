import uuid

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.features.monsters.services.monster_group_service import _family_expected_gear_score


def _monster(
    *,
    clan_id: uuid.UUID,
    role: str = "minion",
    strength: int = 4,
    endurance: int = 6,
    gear_score: int = 20,
    raw_gear_score: int | None = None,
) -> GeneratedMonster:
    return GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan_id,
        variant_id=f"{role}_{strength}",
        member_hash=f"{role}_{strength}",
        role=role,
        title=role,
        short_description=role,
        min_tier=1,
        max_tier=1,
        mongo_actor_key=f"monster:{role}:{strength}",
        active_snapshot={
            "gear_score": gear_score,
            "raw_gear_score": raw_gear_score if raw_gear_score is not None else gear_score,
            "threat_rating": gear_score,
            "scaled_attributes": {
                "strength": strength,
                "agility": 4,
                "endurance": endurance,
                "intellect": 1,
                "memory": 1,
                "mental": 2,
                "perception": 3,
                "projection": 1,
                "prediction": 2,
            },
            "scaled_skills": {"skill_unarmed": 0.2},
            "items": {},
            "vitals": {},
            "ai_profile": {},
        },
        metadata_={"family_id": "rat_swarm", "archetype": "beast", "tags": ["rat"]},
    )


def _armed_monster(*, clan_id: uuid.UUID, skill_value: float) -> GeneratedMonster:
    monster = _monster(clan_id=clan_id, strength=17, endurance=8, gear_score=20 + round(skill_value * 10))
    monster.active_snapshot["scaled_attributes"]["agility"] = 10
    monster.active_snapshot["scaled_skills"] = {"skill_fencing": skill_value}
    monster.active_snapshot["items"] = {
        "layout": {"equipment": {"main_hand": "weapon-1"}},
        "by_id": {
            "weapon-1": {
                "base_id": "test_dagger",
                "item_type": "weapon",
                "slot": "main_hand",
                "combat": {
                    "power": 7,
                    "damage_spread": 0.12,
                    "related_skill": "skill_fencing",
                    "tags": ["weapon", "dagger"],
                },
                "generation": {},
            },
        },
    }
    return monster


def test_apply_monster_gear_score_reads_prebuilt_snapshot_score() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4(), gear_score=37)

    score = service.apply_monster_gear_score(monster)

    assert score == 37


def test_monster_gear_score_is_not_redivided_at_runtime() -> None:
    clan_id = uuid.uuid4()
    service = MonsterGearScoreService()
    solitary = _monster(clan_id=clan_id, gear_score=80, raw_gear_score=80)
    swarm = _monster(clan_id=clan_id, gear_score=20, raw_gear_score=80)

    solitary_score = service.apply_monster_gear_score(solitary)
    swarm_score = service.apply_monster_gear_score(swarm)

    assert solitary_score == 80
    assert swarm_score == 20
    assert swarm.active_snapshot["raw_gear_score"] == solitary.active_snapshot["raw_gear_score"]


def test_monster_gear_score_uses_prebuilt_score_after_mastery() -> None:
    clan_id = uuid.uuid4()
    service = MonsterGearScoreService()
    novice = _armed_monster(clan_id=clan_id, skill_value=0.0)
    master = _armed_monster(clan_id=clan_id, skill_value=1.0)

    assert service.calculate_monster_gear_score(master) > service.calculate_monster_gear_score(novice)


def test_refresh_stale_monster_scores_is_noop_for_prebuilt_snapshots() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4())
    monster.active_snapshot["gear_score"] = 999

    refreshed = service.refresh_stale_monster_scores([monster])

    assert refreshed == 0
    assert monster.active_snapshot["gear_score"] == 999


def test_refresh_stale_monster_scores_keeps_current_version() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4())
    score = service.apply_monster_gear_score(monster)

    refreshed = service.refresh_stale_monster_scores([monster])

    assert refreshed == 0
    assert service.apply_monster_gear_score(monster) == score


def test_apply_clan_summary_groups_scores_by_role() -> None:
    clan_id = uuid.uuid4()
    clan = GeneratedClan(
        id=clan_id,
        family_id="rat_swarm",
        identity_hash="unique",
        context_identity={"tier": 1, "zone_id": "zone-a"},
        context_hash="context",
        selected_traits=[],
        title="Rats",
        description="Rats",
        encounter_texts={},
        generation_version=1,
        resource_version="test",
        members=[
            _monster(clan_id=clan_id, role="minion", strength=4, gear_score=10, raw_gear_score=40),
            _monster(clan_id=clan_id, role="veteran", strength=12, gear_score=30, raw_gear_score=120),
        ],
    )
    service = MonsterGearScoreService()

    summary = service.apply_clan_summary(clan)

    assert summary["count"] == 2
    assert summary["min"] <= summary["avg"] <= summary["max"]
    assert summary["by_role"]["minion"]["count"] == 1
    assert summary["by_role"]["veteran"]["count"] == 1
    assert summary["total"] == 40


def test_family_expected_gear_score_uses_raw_average_and_ignores_assembly_cost() -> None:
    clan_id = uuid.uuid4()
    members = [
        _monster(clan_id=clan_id, role="minion"),
        _monster(clan_id=clan_id, role="veteran"),
        _monster(clan_id=clan_id, role="elite"),
        _monster(clan_id=clan_id, role="boss"),
    ]
    raw_scores = [100, 200, 700, 1000]
    for member, raw_score in zip(members, raw_scores, strict=True):
        member.active_snapshot.update({"raw_gear_score": raw_score, "gear_score": 1, "assembly_cost": 1})

    expected = _family_expected_gear_score(members, tier=5)

    assert expected == 500.0
