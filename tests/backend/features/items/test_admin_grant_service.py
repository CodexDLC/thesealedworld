from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.backend.features.items.dto.instance import GeneratedItemDTO
from src.backend.features.items.services.admin_grant_service import AdminItemGrantService
from src.backend.features.items.services.generation_service import ItemGenerationResultDTO


class FakeSession:
    def __init__(self, character: object | None = None) -> None:
        self.character = character

    async def get(self, _model, _pk):
        return self.character


class FakeItemGeneration:
    def __init__(self, *, text_requested: bool = False) -> None:
        self.requests = []
        self.enriched = []
        self.text_requested = text_requested

    async def generate_mechanical(self, request):
        self.requests.append(request)
        return ItemGenerationResultDTO(
            item_ids=["item-1"],
            items=[
                GeneratedItemDTO(
                    instance_id="item-1",
                    template_id="warhammer:mat_iron_ingot:uncommon",
                    item_type="weapon",
                    rarity="uncommon",
                    rarity_tier=request.rarity_tier,
                    name="Железный боевой молот",
                    description="Тяжелый молот.",
                    base_id=request.base_id,
                    material_id=request.material_id,
                    power=10,
                    durability_max=100,
                    slot="two_hand",
                    metadata={
                        "generated_template_id": "template-1",
                        "text_visual_hash": "hash-1",
                    },
                )
            ],
            text_status="pending" if self.text_requested else "not_requested",
            text_requested_item_ids=["item-1"] if self.text_requested else [],
        )

    async def enrich_text(self, item_id, request):
        self.enriched.append((item_id, request))


@pytest.mark.unit
async def test_admin_grant_service_grants_character_backpack_item() -> None:
    item_generation = FakeItemGeneration()
    service = AdminItemGrantService(
        session=FakeSession(character=SimpleNamespace(character_id=7)),
        item_generation=item_generation,
    )

    result = await service.grant_to_character(char_id=7, base_id="warhammer", rarity_tier=1, material_id="mat_iron_ingot")

    request = item_generation.requests[0]
    assert result.item_id == "item-1"
    assert result.generated_template_id == "template-1"
    assert result.text_visual_hash == "hash-1"
    assert request.placement_ref.holder_type == "character"
    assert request.placement_ref.holder_id == "7"
    assert request.placement_ref.storage_type == "backpack"
    assert request.origin_ref.origin_type == "admin"


@pytest.mark.unit
async def test_admin_grant_service_rejects_missing_character() -> None:
    service = AdminItemGrantService(
        session=FakeSession(character=None),
        item_generation=FakeItemGeneration(),
    )

    with pytest.raises(ValueError, match="Character not found"):
        await service.grant_to_character(char_id=404, base_id="warhammer")


@pytest.mark.unit
async def test_admin_grant_service_enqueues_ai_text_when_requested() -> None:
    item_generation = FakeItemGeneration(text_requested=True)
    service = AdminItemGrantService(
        session=FakeSession(character=SimpleNamespace(character_id=7)),
        item_generation=item_generation,
        generation_ai=AsyncMock(),
    )

    result = await service.grant_to_character(char_id=7, base_id="warhammer", request_ai_text=True)

    assert result.ai_text_task_requested is True
    assert item_generation.enriched[0][0] == "item-1"


@pytest.mark.unit
async def test_admin_grant_service_passes_source_context_and_seed_suffix() -> None:
    item_generation = FakeItemGeneration()
    service = AdminItemGrantService(
        session=FakeSession(character=SimpleNamespace(character_id=7)),
        item_generation=item_generation,
    )

    await service.grant_to_character(
        char_id=7,
        base_id="dagger",
        rarity_tier=2,
        source="admin:bandit_tier2_grant",
        source_context={"monster_family_id": "bandit_gang", "member_tier": 2},
        seed_suffix="2",
    )

    request = item_generation.requests[0]
    assert request.source_context == {"monster_family_id": "bandit_gang", "member_tier": 2}
    assert request.origin_ref.seed == "admin:bandit_tier2_grant:7:dagger:2:auto:auto:2"
