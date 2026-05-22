from __future__ import annotations

import uuid

import pytest

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.services.generated_view_service import GeneratedMonsterViewService


class FakeGeneratedMonsterRepository:
    def __init__(self, clans: list[GeneratedClan]) -> None:
        self.clans = clans

    async def count_generated_clans(self, **kwargs) -> int:
        return len(self.clans)

    async def list_generated_clans_page(self, **kwargs) -> list[GeneratedClan]:
        return self.clans


@pytest.mark.unit
async def test_generated_view_projects_visual_storage_and_equipment_summary() -> None:
    clan_id = uuid.uuid4()
    member_id = uuid.uuid4()
    member = GeneratedMonster(
        id=member_id,
        clan_id=clan_id,
        variant_key="bandit_cutthroat",
        role="minion",
        member_tier=2,
        threat_rating=31,
        name_ru="Cutthroat",
        description="",
        text_content={},
        scaled_attributes={},
        scaled_skills={},
        items={
            "layout": {"equipment": {"main_hand": "knife-1", "body": "coat-1"}},
            "by_id": {
                "knife-1": {"name_ru": "Rust knife", "kind": "weapon", "affixes": ["sharp"]},
                "coat-1": {"name_ru": "Patched coat", "kind": "armor", "affixes": ["worn"]},
            },
        },
        vitals={},
        ai_profile={},
        generation_meta={
            "balance": {"gear_score": 11, "base_cost": 20, "effective_cost": 22.5},
            "visual": {
                "status": "generated",
                "image_url": "/static/generated-assets/monsters/member.webp",
                "storage_key": "monsters/member.webp",
                "storage_backend": "local",
            },
        },
    )
    clan = GeneratedClan(
        id=clan_id,
        family_id="bandit_gang",
        tier=2,
        zone_id="zone-a",
        context_hash="ctx",
        unique_hash="unique",
        raw_tags={},
        flavor_content={
            "visual": {
                "status": "generated",
                "image_url": "/static/generated-assets/monsters/clan.webp",
                "storage_key": "monsters/clan.webp",
                "storage_backend": "local",
            }
        },
        name_ru="Bandits",
        description="A gang",
        members=[member],
    )
    member.clan = clan

    result = await GeneratedMonsterViewService(FakeGeneratedMonsterRepository([clan])).list_generated()

    item = result.items[0]
    assert item.visual.image_url == "/static/generated-assets/monsters/clan.webp"
    assert item.visual.storage_key == "monsters/clan.webp"
    assert item.members[0].visual.image_url == "/static/generated-assets/monsters/member.webp"
    assert item.members[0].equipment_summary.equipment == ["body: Patched coat", "main_hand: Rust knife"]
    assert item.members[0].equipment_summary.weapons == ["main_hand: Rust knife"]
    assert item.members[0].equipment_summary.armor == ["body: Patched coat"]
    assert item.members[0].equipment_summary.affixes == ["sharp", "worn"]
