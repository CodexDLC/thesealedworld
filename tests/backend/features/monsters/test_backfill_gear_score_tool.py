import uuid

from tools.monsters.backfill_gear_score import _apply_member_backfill

from src.backend.features.monsters.dto.generation import GeneratedMonster
from src.backend.infrastructure.monsters import GeneratedMonsterORM


def test_backfill_gear_score_updates_member_threat_rating_with_balance_snapshot() -> None:
    clan_id = uuid.uuid4()
    member_id = uuid.uuid4()
    member_row = GeneratedMonsterORM(
        id=member_id,
        clan_id=clan_id,
        variant_key="goblin_scavenger",
        role="minion",
        member_tier=1,
        threat_rating=43,
        name_ru="Goblin",
        description="Goblin",
        text_content={},
        scaled_attributes={},
        scaled_skills={},
        items={},
        vitals={},
        ai_profile={},
        combat_actor_snapshot={},
        generation_meta={"balance": {"gear_score": 43, "gear_score_version": 7}},
    )
    recalculated = GeneratedMonster(
        id=member_id,
        clan_id=clan_id,
        variant_key="goblin_scavenger",
        role="minion",
        member_tier=1,
        threat_rating=58,
        name_ru="Goblin",
        description="Goblin",
        text_content={},
        scaled_attributes={},
        scaled_skills={},
        items={},
        vitals={},
        ai_profile={},
        generation_meta={
            "balance": {
                "raw_gear_score": 174,
                "assembly_cost": 58,
                "gear_score": 58,
                "gear_score_version": 8,
            }
        },
    )

    _apply_member_backfill(member_row, recalculated)

    assert member_row.threat_rating == 58
    assert member_row.generation_meta["balance"]["gear_score"] == 58
    assert member_row.generation_meta["balance"]["gear_score_version"] == 8
