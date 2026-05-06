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
        affix_bundle_ids=["soldier"],
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
    assert payload["rarity"]["tier"] == 1
    assert payload["affixes"][0]["id"] == "soldier"


@pytest.mark.unit
async def test_item_text_service_skips_ai_when_request_does_not_ask_for_text():
    request = ItemGenerationRequestDTO(base_id="warhammer", rarity_tier=0, request_ai_text=False)
    mechanical_item = ItemFactory().generate(request)
    ai = FakeAI({"name": "Не должен примениться", "description": "Не должен примениться."})

    item = await ItemTextService(ItemTextAIClient(ai)).enrich(mechanical_item, request)

    assert item == mechanical_item
    assert ai.calls == []
