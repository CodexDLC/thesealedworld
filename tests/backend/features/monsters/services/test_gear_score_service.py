import uuid

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService


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
            "balance": {"base_cost": 20, "effective_cost": 4, "threat_rating": 20},
            "meta": {"family_id": "rat_swarm", "archetype": "beast", "tags": ["rat"]},
        },
    )


def test_apply_monster_gear_score_persists_balance_snapshot() -> None:
    service = MonsterGearScoreService()
    monster = _monster(clan_id=uuid.uuid4())

    score = service.apply_monster_gear_score(monster)

    assert score > 0
    assert monster.generation_meta["balance"]["gear_score"] == score
    assert monster.generation_meta["balance"]["gear_score_version"] == MonsterGearScoreService.VERSION
    assert monster.generation_meta["balance"]["base_cost"] == 20


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
