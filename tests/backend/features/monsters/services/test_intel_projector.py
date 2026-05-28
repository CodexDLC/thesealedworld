from __future__ import annotations

from src.backend.features.monsters.dto.generation import MonsterGroupMemberPreview, MonsterGroupResult
from src.backend.features.monsters.intel_projector import MonsterIntelProjector


def test_monster_intel_masks_combat_details_at_low_hunting() -> None:
    group = _group()

    projected = MonsterIntelProjector().project_group(group, hunting_skill=0.0)

    enemy = projected.enemies[0]
    assert enemy.name == "???"
    assert enemy.role == "???"
    assert enemy.hp_percent is None
    assert enemy.threat_rating is None
    assert enemy.intel["vitals"] == {}
    assert enemy.intel["equipment"] == []
    assert enemy.intel["affixes"] == []


def test_monster_intel_reveals_full_combat_preview_at_expert_hunting() -> None:
    group = _group()

    projected = MonsterIntelProjector().project_group(group, hunting_skill=1.0)

    enemy = projected.enemies[0]
    assert enemy.name == "Rat Scout"
    assert enemy.role == "scout"
    assert enemy.threat_rating is None
    assert enemy.intel["danger_band"] == "низкая"
    assert enemy.intel["power"]["gear_score"] == 40
    assert enemy.intel["vitals"]["hp"] == {"current": 12, "max": 12, "label": "12/12"}
    assert enemy.intel["vitals"]["energy"] == {"current": 8, "max": 8, "label": "8/8"}
    assert enemy.intel["vitals"]["concentration"] == {"current": 5, "max": 5, "label": "5/5"}
    assert enemy.intel["equipment"] == [
        {"slot": "main_hand", "kind": "weapon", "label": "rusty_dagger", "tags": ["bleed", "knife"]}
    ]
    assert enemy.intel["affixes"] == [{"affix_id": "serrated", "tier": 1}]
    assert "ambusher" in enemy.intel["traits"]


def _group() -> MonsterGroupResult:
    return MonsterGroupResult(
        group_id="group-1",
        clan_id="clan-1",
        family_id="rat_swarm",
        loc_id="50_50",
        zone_id="D4_0_0",
        biome_id="city_ruins",
        tier=1,
        danger=0.2,
        target_budget=100,
        adjusted_budget=105,
        total_power=40,
        monster_ids=["m1"],
        reused_existing_clan=False,
        context_hash="context",
        unique_hash="unique",
        tags=["city_ruins"],
        previews=[
            MonsterGroupMemberPreview(
                monster_id="m1",
                name="Rat Scout",
                description="A narrow rat with a knife.",
                role="scout",
                variant_key="rat_scout",
                member_tier=1,
                threat_rating=99,
                hp={"current": 12, "max": 12},
                image="/static/generated-assets/rat.webp?v=hash",
                visual={"image_url": "/static/generated-assets/rat.webp?v=hash"},
                tags=["ambusher", "rat"],
                archetype="beast",
                family_id="rat_swarm",
                organization_type="swarm",
                gear_score=40,
                vitals={
                    "hp": {"current": 12, "max": 12},
                    "energy": {"current": 8, "max": 8},
                    "concentration": {"current": 5, "max": 5},
                },
                equipment=[
                    {"slot": "main_hand", "kind": "weapon", "label": "rusty_dagger", "tags": ["bleed", "knife"]}
                ],
                affixes=[{"affix_id": "serrated", "tier": 1}],
            )
        ],
    )
