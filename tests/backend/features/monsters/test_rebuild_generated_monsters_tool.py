import uuid

from tools.monsters.rebuild_generated_monsters import _apply_member_rebuild, _context_from_clan_row

from src.backend.features.monsters.dto.generation import GeneratedMonster
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


def test_rebuild_tool_preserves_existing_member_visual() -> None:
    member_id = uuid.uuid4()
    clan_id = uuid.uuid4()
    member_row = GeneratedMonsterORM(
        id=member_id,
        clan_id=clan_id,
        variant_key="bandit_poacher",
        role="minion",
        member_tier=0,
        threat_rating=10,
        name_ru="Old Poacher",
        description="Old text",
        text_content={"name_ru": "Old Poacher"},
        scaled_attributes={"strength": 1},
        scaled_skills={"skill_archery": 0.1},
        items={"layout": {"equipment": {"two_hand": "old-bow"}}},
        vitals={"hp": {"max": 10}},
        ai_profile={},
        generation_meta={
            "visual": {
                "status": "generated",
                "image_url": "/static/generated-assets/monsters/generated/members/old.webp",
            },
            "balance": {"gear_score": 10},
        },
        combat_actor_snapshot={"old": True},
    )
    rebuilt = GeneratedMonster(
        id=member_id,
        clan_id=clan_id,
        variant_key="bandit_poacher",
        role="minion",
        member_tier=1,
        threat_rating=22,
        name_ru="New Poacher",
        description="New text",
        text_content={"name_ru": "New Poacher"},
        scaled_attributes={"strength": 8},
        scaled_skills={"skill_archery": 0.1429, "skill_ranged_combat": 0.1429},
        items={"layout": {"equipment": {"two_hand": "new-bow", "quiver": "new-quiver"}}},
        vitals={"hp": {"max": 20}},
        ai_profile={"range": "ranged"},
        generation_meta={
            "visual": {"status": "fallback", "image_url": "/static/images/monsters/families/bandit_gang.svg"},
            "balance": {"gear_score": 22},
        },
        combat_actor_snapshot={},
    )

    _apply_member_rebuild(member_row, rebuilt)

    assert member_row.name_ru == "Old Poacher"
    assert member_row.threat_rating == 22
    assert member_row.scaled_skills == {"skill_archery": 0.1429, "skill_ranged_combat": 0.1429}
    assert member_row.items["layout"]["equipment"]["quiver"] == "new-quiver"
    assert member_row.generation_meta["balance"] == {"gear_score": 22}
    assert member_row.generation_meta["visual"] == {
        "status": "generated",
        "image_url": "/static/generated-assets/monsters/generated/members/old.webp",
    }


def test_rebuild_tool_restores_generation_context_from_clan_raw_tags() -> None:
    clan_row = GeneratedClanORM(
        id=uuid.uuid4(),
        family_id="bandit_gang",
        tier=2,
        zone_id="D4_0_1",
        biome_id=None,
        context_hash="ctx",
        unique_hash="unique",
        raw_tags={
            "biome_id": "city_ruins",
            "tags": ["bandit_gang", "unknown_noise"],
            "difficulty": "hard",
            "context_meta": {"danger": 0.4},
        },
        flavor_content={},
        name_ru="Bandits",
        description="Bandits",
    )

    context = _context_from_clan_row(clan_row)

    assert context.zone_id == "D4_0_1"
    assert context.biome_id == "city_ruins"
    assert context.tier == 2
    assert context.tags == ["bandit_gang", "unknown_noise"]
    assert context.difficulty == "hard"
    assert context.context_meta == {"danger": 0.4}
