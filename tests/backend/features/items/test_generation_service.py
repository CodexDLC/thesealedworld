from types import SimpleNamespace

import pytest

from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemPlacementRefDTO
from src.backend.features.items.events import _parse_generation_requests
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.services.generation_service import ItemGenerationService


class FakeRepo:
    def __init__(self) -> None:
        self.instances = {}
        self.templates_by_hash = {}
        self.created_templates = []

    async def create_mechanical(
        self,
        item,
        placement_ref,
        *,
        text_status,
        origin_ref=None,
        correlation_id=None,
        generated_template_id=None,
    ):
        instance_id = f"item-{len(self.instances) + 1}"
        instance = FakeInstance(
            id=instance_id,
            generated_template_id=generated_template_id,
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

    async def get_text_visual_template_by_hash(self, text_visual_hash):
        return self.templates_by_hash.get(text_visual_hash)

    async def create_text_visual_template(
        self,
        item,
        *,
        text_visual_hash,
        text_payload,
        prompt_version,
        text_status,
    ):
        template = FakeInstance(
            id=f"template-{len(self.created_templates) + 1}",
            text_visual_hash=text_visual_hash,
            name=item.name,
            description=item.description,
            text_status=text_status,
            text_payload=text_payload,
            prompt_version=prompt_version,
        )
        self.templates_by_hash[text_visual_hash] = template
        self.created_templates.append(template)
        return template

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


class FakeGenerationAI:
    def __init__(self) -> None:
        self.specs = []

    async def enqueue_many(self, specs):
        self.specs.extend(specs)


class FakeTemplatePersistence:
    def __init__(self) -> None:
        self.templates_by_hash = {}
        self.created_templates = []
        self.created_items = []

    async def get_text_visual_template_by_hash(self, text_visual_hash):
        return self.templates_by_hash.get(text_visual_hash)

    async def create_text_visual_template(self, item, *, text_visual_hash, text_payload, prompt_version, text_status):
        template = SimpleNamespace(
            id=f"template-{len(self.created_templates) + 1}",
            text_visual_hash=text_visual_hash,
            name=item.name,
            description=item.description,
            appearance=dict(item.metadata),
            generation={
                "material_id": item.material_id,
                "affix_bundle_ids": list(item.affix_bundle_ids),
                "narrative_tags": list(item.narrative_tags),
            },
            metadata=dict(item.metadata),
            text_status=text_status,
        )
        self.templates_by_hash[text_visual_hash] = template
        self.created_templates.append(template)
        return template

    async def create_mechanical_item(
        self,
        item,
        placement_ref,
        *,
        text_status,
        origin_ref=None,
        generated_template_id=None,
    ):
        item_id = f"item-{len(self.created_items) + 1}"
        self.created_items.append(
            {
                "item_id": item_id,
                "item": item,
                "placement_ref": placement_ref,
                "text_status": text_status,
                "origin_ref": origin_ref,
                "generated_template_id": generated_template_id,
            }
        )
        return item_id


@pytest.mark.unit
async def test_generation_service_creates_mechanical_item_without_returning_payload_when_forwarded():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        rarity_tier=2,
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
async def test_generation_service_reuses_text_visual_template_when_affixes_differ():
    persistence = FakeTemplatePersistence()
    service = ItemGenerationService(persistence)
    base_request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=2,
        request_ai_text=True,
        source_context={"family_id": "bandit_gang", "member_role": "bruiser", "member_tier": 2},
        placement_ref=ItemPlacementRefDTO(holder_type="system", holder_id="loot", storage_type="backpack"),
    )

    first = await service.generate_mechanical(
        base_request.model_copy(update={"forced_affix_ids": ["crit_chance"], "affix_count": 1})
    )
    second = await service.generate_mechanical(
        base_request.model_copy(update={"forced_affix_ids": ["weapon_accuracy"], "affix_count": 1})
    )

    assert first.item_ids == ["item-1"]
    assert second.item_ids == ["item-2"]
    assert len(persistence.created_templates) == 1
    assert persistence.created_items[0]["generated_template_id"] == "template-1"
    assert persistence.created_items[1]["generated_template_id"] == "template-1"


@pytest.mark.unit
async def test_generation_service_creates_character_owned_instances_from_reused_template():
    persistence = FakeTemplatePersistence()
    service = ItemGenerationService(persistence)
    base_request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=2,
        request_ai_text=True,
        source_context={"monster_family_id": "bandit_gang", "member_role": "bruiser", "member_tier": 2},
        placement_ref=ItemPlacementRefDTO(holder_type="character", holder_id="7", storage_type="backpack"),
    )

    first = await service.generate_mechanical(
        base_request.model_copy(update={"forced_affix_ids": ["crit_chance"], "affix_count": 1})
    )
    second = await service.generate_mechanical(
        base_request.model_copy(update={"forced_affix_ids": ["weapon_accuracy"], "affix_count": 1})
    )

    assert first.item_ids == ["item-1"]
    assert second.item_ids == ["item-2"]
    assert first.text_requested_item_ids == ["item-1"]
    assert second.text_requested_item_ids == []
    assert len(persistence.created_templates) == 1
    for created in persistence.created_items:
        assert created["generated_template_id"] == "template-1"
        assert created["placement_ref"].holder_type == "character"
        assert created["placement_ref"].holder_id == "7"
        assert created["placement_ref"].storage_type == "backpack"


@pytest.mark.unit
async def test_generation_service_reuses_text_template_for_same_clan_item_keys_across_locations():
    persistence = FakeTemplatePersistence()
    service = ItemGenerationService(persistence)
    base_request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=2,
        request_ai_text=True,
        source_context={
            "clan_id": "clan-1",
            "location_id": "52_53",
            "source_tier": 2,
            "owner_family": {"clan_id": "clan-1", "loot_culture": {"craft_style": "rough salvage"}},
        },
        placement_ref=ItemPlacementRefDTO(holder_type="system", holder_id="loot", storage_type="backpack"),
    )

    first = await service.generate_mechanical(base_request)
    second = await service.generate_mechanical(
        base_request.model_copy(
            update={
                "source_context": {
                    "clan_id": "clan-1",
                    "location_id": "different_location",
                    "source_tier": 99,
                    "owner_family": {"clan_id": "clan-1", "loot_culture": {"craft_style": "changed prompt data"}},
                }
            }
        )
    )

    assert first.item_ids == ["item-1"]
    assert second.item_ids == ["item-2"]
    assert len(persistence.created_templates) == 1
    assert persistence.created_items[0]["item"].metadata["text_template_hash_payload"] == {
        "clan_id": "clan-1",
        "base_id": "warhammer",
        "item_tier": 2,
        "material_id": "mat_iron_ingot",
    }
    assert persistence.created_items[1]["generated_template_id"] == "template-1"


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
        item_grade="no_grade",
        affix_profile="monster_equipment_4slot",
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
            item_grade="uncommon",
            affix_profile="monster_equipment_4slot",
            allowed_affix_ids=["weapon_accuracy", "crit_chance"],
            forced_affix_ids=["weapon_accuracy"],
            affix_count=4,
            affix_step_count=2,
            runtime_metadata={"owner_key": "member_0", "runtime_item_id": "item-main"},
        ),
        ItemGenerationRequestDTO(
            generation_mode="runtime",
            base_id="leather_armor",
            item_grade="uncommon",
            affix_profile="monster_equipment_4slot",
            allowed_affix_ids=["evasion_bonus", "physical_resistance_bonus"],
            forced_affix_ids=["evasion_bonus"],
            affix_count=4,
            affix_step_count=2,
            runtime_metadata={"owner_key": "member_0", "runtime_item_id": "item-armor"},
        ),
    ]

    projections = await service.generate_runtime_projections(requests)

    assert [item.item_id for item in projections] == ["item-main", "item-armor"]
    assert [item.owner_key for item in projections] == ["member_0", "member_0"]
    assert set(projections[0].combat.bonuses) == {"crit_chance", "main_hand_accuracy"}
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
                    "item_grade": "common",
                    "affix_profile": "monster_equipment_4slot",
                    "affix_step_count": 2,
                    "presentation_name_ru": "Крысиные клыки",
                    "runtime_metadata": {"monster_equipment_key": "rat_bite_claws"},
                }
            ]
        }
    )

    assert requests[0].generation_mode == "runtime"
    assert requests[0].affix_profile == "monster_equipment_4slot"
    assert requests[0].affix_step_count == 2
    assert requests[0].presentation_name_ru == "Крысиные клыки"
    assert requests[0].runtime_metadata["monster_equipment_key"] == "rat_bite_claws"


@pytest.mark.unit
async def test_generation_service_forces_common_tier_ready_even_when_ai_text_is_requested():
    repo = FakeRepo()
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=0, request_ai_text=True)

    result = await ItemGenerationService(ItemPersistenceIntegration(repo)).generate_mechanical(request)
    item = await ItemGenerationService(ItemPersistenceIntegration(repo)).enrich_text(result.item_ids[0], request)

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

    result = await ItemGenerationService(ItemPersistenceIntegration(repo)).generate_mechanical(request)

    assert result.text_status == "not_requested"
    assert repo.instances["item-1"].text_status == "not_requested"
    assert repo.instances["item-1"].lifecycle_status == "ready"


@pytest.mark.unit
async def test_generation_service_allows_ai_text_when_grade_overrides_tier_zero():
    repo = FakeRepo()
    generation_ai = FakeGenerationAI()
    service = ItemGenerationService(ItemPersistenceIntegration(repo), generation_ai=generation_ai)
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
    assert item.name == "Ржавый боевой молот"
    assert repo.instances["item-1"].text_status == "pending"
    assert len(generation_ai.specs) == 1
    assert generation_ai.specs[0].task_type == "items.text"


@pytest.mark.unit
async def test_generation_service_enqueues_item_text_task_after_mechanical_item_exists():
    repo = FakeRepo()
    generation_ai = FakeGenerationAI()
    service = ItemGenerationService(ItemPersistenceIntegration(repo), generation_ai=generation_ai)
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=2, request_ai_text=True)
    result = await service.generate_mechanical(request)

    item = await service.enrich_text(result.item_ids[0], request)

    assert item is not None
    assert item.name == repo.instances["item-1"].name
    instance = repo.instances["item-1"]
    assert instance.text_status == "pending"
    assert instance.lifecycle_status == "mechanical_ready"
    assert len(generation_ai.specs) == 1
    assert generation_ai.specs[0].task_type == "items.text"
