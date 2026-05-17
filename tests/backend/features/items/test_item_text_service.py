from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.runtime.item_factory import ItemFactory
from src.backend.features.items.services.text_service import ItemTextService


def test_item_text_service_builds_prompt_payload_from_mechanical_item():
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=1,
        source="scenario:awakening_rift",
        request_ai_text=True,
    )
    mechanical_item = ItemFactory().generate(request)

    payload = ItemTextService()._build_payload(mechanical_item, request)

    assert payload["base"]["id"] == "warhammer"
    assert payload["base"]["narrative_description"]
    assert payload["material"]["id"] == "mat_iron_ingot"
    assert payload["grade"] == "uncommon"
    assert isinstance(payload["affixes"], list)


def test_item_text_service_passes_source_context_in_payload():
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

    payload = ItemTextService()._build_payload(mechanical_item, request)

    assert payload["source_context"]["monster_family_id"] == "bandit_gang"
    assert payload["source_context"]["biome_id"] == "city_ruins"
