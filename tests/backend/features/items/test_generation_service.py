import json

import pytest

from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemPlacementRefDTO
from src.backend.features.items.events import _parse_generation_requests
from src.backend.features.items.integrations import ItemPersistenceIntegration, ItemTextAIClient
from src.backend.features.items.services.generation_service import ItemGenerationService


class FakeRepo:
    def __init__(self) -> None:
        self.instances = {}

    async def create_mechanical(self, item, placement_ref, *, text_status, origin_ref=None, correlation_id=None):
        instance = FakeInstance(
            id="item-1",
            base_id=item.base_id,
            item_type=item.item_type,
            rarity=item.rarity,
            rarity_tier=item.rarity_tier,
            lifecycle_status="ready" if text_status == "not_requested" else "mechanical_ready",
            text_status=text_status,
            name=item.name,
            description=item.description,
            mechanics={
                **item.mechanics,
                "template_id": item.template_id,
                "slot": item.slot,
                "valid_slots": item.valid_slots,
                "power": item.power,
                "durability_max": item.durability_max,
                "damage_spread": item.damage_spread,
                "implicit_bonuses": item.implicit_bonuses,
                "bonuses": item.bonuses,
                "triggers": item.triggers,
            },
            appearance={"width_cells": 1, "height_cells": 1, "volume_units": 1, "icon_key": None},
            generation={
                "material_id": item.material_id,
                "affix_bundle_ids": item.affix_bundle_ids,
                "narrative_tags": item.narrative_tags,
            },
            metadata_=item.metadata,
        )
        self.instances[instance.id] = instance
        self.placement = placement_ref
        self.origin = origin_ref
        return instance

    async def get(self, item_id):
        return self.instances.get(item_id)

    async def update_text(self, item_id, *, name, description, text_status):
        instance = self.instances[item_id]
        instance.name = name
        instance.description = description
        instance.text_status = text_status
        if text_status == "generated":
            instance.lifecycle_status = "ready"
        return instance

    async def mark_text_failed(self, item_id, reason=None):
        instance = self.instances[item_id]
        instance.text_status = "failed"
        instance.metadata_ = {**instance.metadata_, "ai_text_status": "failed", "ai_text_reason": reason}
        return instance


class FakeInstance:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeAI:
    async def generate_json(self, prompt, *, schema, **kwargs):
        return schema.model_validate(
            json.loads('{"name": "Молот Памяти", "description": "Тяжелый молот с холодной рукоятью."}')
        )


@pytest.mark.unit
async def test_generation_service_creates_mechanical_item_without_returning_payload_when_forwarded():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        rarity_tier=1,
        request_ai_text=True,
        delivery_mode="forward",
        return_item=False,
        placement_ref=ItemPlacementRefDTO(
            holder_type="scenario_reward",
            holder_id="awakening_rift:8",
            storage_type="reward",
        ),
    )

    result = await ItemGenerationService(ItemPersistenceIntegration(repo)).generate_mechanical(request)

    assert result.item_ids == ["item-1"]
    assert result.item is None
    assert result.text_status == "pending"
    instance = repo.instances["item-1"]
    assert instance.lifecycle_status == "mechanical_ready"
    assert instance.text_status == "pending"
    assert repo.placement.holder_type == "scenario_reward"
    assert repo.placement.holder_id == "awakening_rift:8"
    assert repo.placement.storage_type == "reward"


@pytest.mark.unit
async def test_generation_service_marks_item_ready_when_ai_text_is_not_requested():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=0, request_ai_text=False)

    result = await ItemGenerationService(ItemPersistenceIntegration(repo)).generate_mechanical(request)

    assert result.text_status == "not_requested"
    assert result.item is not None
    assert result.item.name == "Ржавый боевой молот"
    assert (
        result.item.description
        == "Двуручный молот, переносящий силу удара в сокрушительный импульс против брони и щитов."
    )
    assert repo.instances["item-1"].name == "Ржавый боевой молот"
    assert repo.instances["item-1"].lifecycle_status == "ready"


@pytest.mark.unit
async def test_generation_service_generates_runtime_item_without_persistence():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(
        generation_mode="runtime",
        base_id="dagger",
        item_grade="artifact",
        affix_bundle_ids=["duelist_weapon_4"],
        affix_step_count=1,
        presentation_name_ru="Крысиные клыки",
        runtime_metadata={"monster_equipment_key": "rat_bite_claws"},
    )

    result = await ItemGenerationService(ItemPersistenceIntegration(repo)).generate(request)

    assert result.item_ids == []
    assert result.text_status == "not_requested"
    assert result.item is not None
    assert result.item.name == "Крысиные клыки"
    assert result.item.metadata["runtime_item"] is True
    assert result.item.metadata["monster_equipment_key"] == "rat_bite_claws"
    assert {affix["roll"]["step_count"] for affix in result.item.mechanics["affixes"]} == {1}
    assert repo.instances == {}


@pytest.mark.unit
async def test_generation_service_generates_runtime_projection_batch_without_persistence():
    repo = FakeRepo()
    service = ItemGenerationService(ItemPersistenceIntegration(repo))
    requests = [
        ItemGenerationRequestDTO(
            generation_mode="runtime",
            base_id="dagger",
            target_slot="main_hand",
            item_grade="artifact",
            allowed_affix_ids=["weapon_accuracy", "crit_chance"],
            forced_affix_ids=["weapon_accuracy"],
            affix_count=1,
            affix_step_count=2,
            runtime_metadata={"owner_key": "member_0", "runtime_item_id": "item-main"},
        ),
        ItemGenerationRequestDTO(
            generation_mode="runtime",
            base_id="leather_armor",
            item_grade="artifact",
            allowed_affix_ids=["evasion_bonus", "physical_resistance_bonus"],
            forced_affix_ids=["evasion_bonus"],
            affix_count=1,
            affix_step_count=2,
            runtime_metadata={"owner_key": "member_0", "runtime_item_id": "item-armor"},
        ),
    ]

    projections = await service.generate_runtime_projections(requests)

    assert [item.item_id for item in projections] == ["item-main", "item-armor"]
    assert [item.owner_key for item in projections] == ["member_0", "member_0"]
    assert set(projections[0].combat.bonuses) == {"main_hand_accuracy"}
    assert set(projections[1].combat.bonuses) == {"evasion"}
    assert repo.instances == {}


@pytest.mark.unit
def test_item_generation_stream_parser_preserves_runtime_fields() -> None:
    requests = _parse_generation_requests(
        {
            "items": [
                {
                    "generation_mode": "runtime",
                    "base_id": "dagger",
                    "item_grade": "artifact",
                    "affix_step_count": 2,
                    "presentation_name_ru": "Крысиные клыки",
                    "runtime_metadata": {"monster_equipment_key": "rat_bite_claws"},
                }
            ]
        }
    )

    assert requests[0].generation_mode == "runtime"
    assert requests[0].affix_step_count == 2
    assert requests[0].presentation_name_ru == "Крысиные клыки"
    assert requests[0].runtime_metadata["monster_equipment_key"] == "rat_bite_claws"


@pytest.mark.unit
async def test_generation_service_forces_common_tier_ready_even_when_ai_text_is_requested():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=0, request_ai_text=True)

    result = await ItemGenerationService(
        ItemPersistenceIntegration(repo), ItemTextAIClient(FakeAI())
    ).generate_mechanical(request)
    item = await ItemGenerationService(ItemPersistenceIntegration(repo), ItemTextAIClient(FakeAI())).enrich_text(
        result.item_ids[0], request
    )

    assert result.text_status == "not_requested"
    assert item is not None
    assert item.name == "Ржавый боевой молот"
    assert repo.instances["item-1"].text_status == "not_requested"
    assert repo.instances["item-1"].lifecycle_status == "ready"


@pytest.mark.unit
async def test_generation_service_uses_item_grade_for_ai_text_threshold():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        rarity_tier=1,
        item_grade="common",
        request_ai_text=True,
    )

    result = await ItemGenerationService(
        ItemPersistenceIntegration(repo), ItemTextAIClient(FakeAI())
    ).generate_mechanical(request)

    assert result.text_status == "not_requested"
    assert repo.instances["item-1"].text_status == "not_requested"
    assert repo.instances["item-1"].lifecycle_status == "ready"


@pytest.mark.unit
async def test_generation_service_allows_ai_text_when_grade_overrides_tier_zero():
    repo = FakeRepo()
    service = ItemGenerationService(ItemPersistenceIntegration(repo), ItemTextAIClient(FakeAI()))
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        rarity_tier=0,
        item_grade="uncommon",
        request_ai_text=True,
    )

    result = await service.generate_mechanical(request)
    item = await service.enrich_text(result.item_ids[0], request)

    assert result.text_status == "pending"
    assert item is not None
    assert item.name == "Молот Памяти"
    assert repo.instances["item-1"].text_status == "generated"


@pytest.mark.unit
async def test_generation_service_updates_text_after_mechanical_item_exists():
    repo = FakeRepo()
    service = ItemGenerationService(ItemPersistenceIntegration(repo), ItemTextAIClient(FakeAI()))
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=1, request_ai_text=True)
    result = await service.generate_mechanical(request)

    item = await service.enrich_text(result.item_ids[0], request)

    assert item is not None
    assert item.name == "Молот Памяти"
    instance = repo.instances["item-1"]
    assert instance.name == "Молот Памяти"
    assert instance.text_status == "generated"
    assert instance.lifecycle_status == "ready"
