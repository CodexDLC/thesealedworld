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
) -> GeneratedMonster:
    return GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=clan_id,
        variant_key=f"{role}_{strength}",
        role=role,
        member_tier=1,
        threat_rating=20,
        name_ru=role,
        description=role,
        text_content={},
        scaled_attributes={
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
        scaled_skills={"skill_unarmed": 0.2},
        items={},
        vitals={},
        ai_profile={},
        generation_meta={
            "schema_version": 2,
            "balance": {
                "base_cost": 20,
                "effective_cost": 4,
                "threat_rating": 20,
                "organization_divisor": 4,
            },
            "meta": {"family_id": "rat_swarm", "archetype": "beast", "tags": ["rat"]},
        },
    )


def _armed_monster(*, clan_id: uuid.UUID, skill_value: float) -> GeneratedMonster:
    monster = _monster(clan_id=clan_id, strength=17, endurance=8)
    monster.scaled_attributes["agility"] = 10
    monster.scaled_skills = {"skill_fencing": skill_value}
    monster.items = {
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


def test_apply_monster_gear_score_persists_balance_snapshot() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4())

    score = service.apply_monster_gear_score(monster)

    assert score > 0
    assert monster.generation_meta["balance"]["gear_score"] == score
    assert monster.generation_meta["balance"]["assembly_cost"] == score
    assert monster.generation_meta["balance"]["raw_gear_score"] >= score
    assert monster.generation_meta["balance"]["gear_score_version"] == MonsterGearScoreService.VERSION
    assert monster.threat_rating == score
    assert "base_cost" not in monster.generation_meta["balance"]
    assert "effective_cost" not in monster.generation_meta["balance"]
    assert "threat_rating" not in monster.generation_meta["balance"]


def test_monster_gear_score_is_divided_by_organization_divisor() -> None:
    clan_id = uuid.uuid4()
    service = MonsterGearScoreService()
    solitary = _monster(clan_id=clan_id)
    solitary.generation_meta["balance"]["organization_divisor"] = 1
    swarm = _monster(clan_id=clan_id)
    swarm.generation_meta["balance"]["organization_divisor"] = 4

    solitary_score = service.apply_monster_gear_score(solitary)
    swarm_score = service.apply_monster_gear_score(swarm)

    assert swarm_score == max(1, round(solitary_score / 4))
    assert swarm.generation_meta["balance"]["raw_gear_score"] == solitary.generation_meta["balance"]["raw_gear_score"]


def test_monster_gear_score_uses_assembled_weapon_power_after_mastery() -> None:
    clan_id = uuid.uuid4()
    service = MonsterGearScoreService()
    novice = _armed_monster(clan_id=clan_id, skill_value=0.0)
    master = _armed_monster(clan_id=clan_id, skill_value=1.0)

    assert service.calculate_monster_gear_score(master) > service.calculate_monster_gear_score(novice)


def test_refresh_stale_monster_scores_replaces_old_balance_version() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4())
    monster.generation_meta["balance"]["gear_score"] = 999
    monster.generation_meta["balance"]["gear_score_version"] = MonsterGearScoreService.VERSION - 1

    refreshed = service.refresh_stale_monster_scores([monster])

    assert refreshed == 1
    assert monster.generation_meta["balance"]["gear_score"] != 999
    assert monster.generation_meta["balance"]["gear_score_version"] == MonsterGearScoreService.VERSION


def test_refresh_stale_monster_scores_keeps_current_version() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4())
    service.apply_monster_gear_score(monster)
    score = monster.generation_meta["balance"]["gear_score"]

    refreshed = service.refresh_stale_monster_scores([monster])

    assert refreshed == 0
    assert monster.generation_meta["balance"]["gear_score"] == score


def test_apply_clan_summary_groups_scores_by_role() -> None:
    clan_id = uuid.uuid4()
    clan = GeneratedClan(
        id=clan_id,
        family_id="rat_swarm",
        tier=1,
        zone_id="zone-a",
        context_hash="context",
        unique_hash="unique",
        raw_tags={},
        flavor_content={},
        name_ru="Rats",
        description="Rats",
        members=[
            _monster(clan_id=clan_id, role="minion", strength=4),
            _monster(clan_id=clan_id, role="veteran", strength=12),
        ],
    )
    service = MonsterGearScoreService()
    for member in clan.members:
        service.apply_monster_gear_score(member)

    summary = service.apply_clan_summary(clan)

    assert clan.raw_tags["gear_score_summary"] == summary
    assert summary["count"] == 2
    assert summary["min"] <= summary["avg"] <= summary["max"]
    assert summary["by_role"]["minion"]["count"] == 1
    assert summary["by_role"]["veteran"]["count"] == 1
    assert summary["raw_count"] == 2
    assert summary["raw_total"] >= summary["total"]
    assert summary["raw_avg"] >= summary["avg"]
    assert summary["raw_by_role"]["minion"]["count"] == 1
    assert summary["raw_by_role"]["veteran"]["count"] == 1


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
        member.generation_meta["balance"].update(
            {
                "organization_type": "swarm",
                "organization_divisor": 4,
                "raw_gear_score": raw_score,
                "gear_score": 1,
                "assembly_cost": 1,
                "gear_score_version": MonsterGearScoreService.VERSION,
            }
        )

    expected = _family_expected_gear_score(members, tier=5)

    assert expected == 500.0
