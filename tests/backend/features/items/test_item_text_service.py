import json

import pytest

from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.integrations import ItemTextAIClient
from src.backend.features.items.runtime.item_factory import ItemFactory
from src.backend.features.items.services.text_service import ItemTextService


class FakeAI:
    def __init__(self, response: object) -> None:
        self.response = response
        self.included_router = None
        self.calls = []

    def include_router(self, router: object) -> None:
        self.included_router = router

    async def process(self, prompt_name: str, **kwargs: object) -> object:
        self.calls.append((prompt_name, kwargs))
        return self.response


@pytest.mark.unit
async def test_item_text_service_replaces_only_name_and_description_with_ai_text():
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=1,
        source="scenario:awakening_rift",
        request_ai_text=True,
    )
    mechanical_item = ItemFactory().generate(request)
    ai = FakeAI(
        json.dumps(
            {
                "name": "Железный Узловой Молот",
                "description": "Тяжелый молот с тусклым железным сердцем. Его рукоять помнит первый страх носителя.",
            },
            ensure_ascii=False,
        )
    )

    item = await ItemTextService(ItemTextAIClient(ai)).enrich(mechanical_item, request)

    assert item.name == "Железный Узловой Молот"
    assert item.description.startswith("Тяжелый молот")
    assert item.power == mechanical_item.power
    assert item.durability_max == mechanical_item.durability_max
    assert item.bonuses == mechanical_item.bonuses
    assert item.metadata["ai_text_status"] == "generated"
    assert ai.calls[0][0] == "item_name_description"
    payload = ai.calls[0][1]["payload"]
    assert payload["base"]["id"] == "warhammer"
    assert payload["base"]["narrative_description"]
    assert payload["material"]["id"] == "mat_iron_ingot"
    assert payload["grade"] == "uncommon"
    assert isinstance(payload["affixes"], list)


@pytest.mark.unit
async def test_item_text_service_accepts_fenced_json_ai_response():
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=1,
        source="scenario:awakening_rift",
        request_ai_text=True,
    )
    mechanical_item = ItemFactory().generate(request)
    ai = FakeAI(
        """```json
{
  "name": "Грязный железный молот",
  "description": "Когда-то он, возможно, был ровным и надежным."
}
```"""
    )

    item = await ItemTextService(ItemTextAIClient(ai)).enrich(mechanical_item, request)

    assert item.name == "Грязный железный молот"
    assert item.description.startswith("Когда-то он")
    assert item.metadata["ai_text_status"] == "generated"


@pytest.mark.unit
async def test_item_text_service_skips_ai_when_request_does_not_ask_for_text():
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=0, request_ai_text=False)
    mechanical_item = ItemFactory().generate(request)
    ai = FakeAI({"name": "Не должен примениться", "description": "Не должен примениться."})

    item = await ItemTextService(ItemTextAIClient(ai)).enrich(mechanical_item, request)

    assert item == mechanical_item
    assert ai.calls == []


@pytest.mark.unit
async def test_item_text_service_skips_ai_for_common_grade_even_when_requested():
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=0, request_ai_text=True)
    mechanical_item = ItemFactory().generate(request)
    ai = FakeAI({"name": "Не должен примениться", "description": "Не должен примениться."})

    item = await ItemTextService(ItemTextAIClient(ai)).enrich(mechanical_item, request)

    assert item.name == mechanical_item.name
    assert item.description == mechanical_item.description
    assert item.metadata["ai_text_status"] == "skipped"
    assert item.metadata["ai_text_reason"] == "common_tier"
    assert ai.calls == []


@pytest.mark.unit
async def test_item_text_service_passes_source_context_in_payload():
    source_context = {
        "monster_family_id": "bandit_gang",
        "monster_family_tags": ["human", "outlaw"],
        "biome_id": "city_ruins",
        "source_label": "loot",
    }
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=1,
        request_ai_text=True,
        source_context=source_context,
    )
    mechanical_item = ItemFactory().generate(request)
    ai = FakeAI(
        json.dumps(
            {"name": "Лезвие Банды", "description": "Оружие из рук придорожного головореза."}, ensure_ascii=False
        )
    )

    await ItemTextService(ItemTextAIClient(ai)).enrich(mechanical_item, request)

    payload = ai.calls[0][1]["payload"]
    assert payload["source_context"]["monster_family_id"] == "bandit_gang"
    assert payload["source_context"]["biome_id"] == "city_ruins"
