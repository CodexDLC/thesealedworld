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
    assert "affixes" not in payload


def test_item_text_service_payload_ignores_affix_rolls_for_template_reuse():
    request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=1,
        source_context={"family_id": "bandit_gang", "member_role": "bruiser", "member_tier": 2},
        request_ai_text=True,
    )
    first = ItemFactory().generate(
        request.model_copy(
            update={
                "forced_affix_ids": ["crit_chance"],
                "affix_count": 1,
            }
        )
    )
    second = ItemFactory().generate(
        request.model_copy(
            update={
                "forced_affix_ids": ["weapon_accuracy"],
                "affix_count": 1,
            }
        )
    )

    assert ItemTextService()._build_payload(first, request) == ItemTextService()._build_payload(second, request)


def test_item_text_service_template_hash_uses_only_clan_base_tier_material():
    service = ItemTextService()
    first_request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=2,
        request_ai_text=True,
        source_context={
            "clan_id": "clan-1",
            "location_id": "52_53",
            "source_tier": 7,
            "owner_family": {
                "clan_id": "clan-1",
                "clan_name_ru": "Банда Воротной Щепы",
                "loot_culture": {"craft_style": "грубая переделка найденных вещей"},
            },
        },
    )
    second_request = first_request.model_copy(
        update={
            "source_context": {
                "clan_id": "clan-1",
                "location_id": "rift_999",
                "source_tier": 12,
                "owner_family": {
                    "clan_id": "clan-1",
                    "clan_name_ru": "Другое отображаемое имя",
                    "loot_culture": {"craft_style": "другой prompt context"},
                },
            }
        }
    )
    first_item = ItemFactory().generate(first_request)
    second_item = ItemFactory().generate(second_request)

    first_hash_payload = service._build_template_hash_payload(first_item, first_request)
    second_hash_payload = service._build_template_hash_payload(second_item, second_request)

    assert first_hash_payload == {
        "clan_id": "clan-1",
        "base_id": "warhammer",
        "item_tier": 2,
        "material_id": "mat_iron_ingot",
    }
    assert first_hash_payload == second_hash_payload
    assert service.build_text_visual_hash(first_hash_payload) == service.build_text_visual_hash(second_hash_payload)


def test_item_text_service_template_hash_changes_by_clan_id():
    service = ItemTextService()
    first_request = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        rarity_tier=2,
        request_ai_text=True,
        source_context={"clan_id": "clan-1"},
    )
    second_request = first_request.model_copy(update={"source_context": {"clan_id": "clan-2"}})
    first_item = ItemFactory().generate(first_request)
    second_item = ItemFactory().generate(second_request)

    first_hash_payload = service._build_template_hash_payload(first_item, first_request)
    second_hash_payload = service._build_template_hash_payload(second_item, second_request)

    assert first_hash_payload["clan_id"] == "clan-1"
    assert second_hash_payload["clan_id"] == "clan-2"
    assert service.build_text_visual_hash(first_hash_payload) != service.build_text_visual_hash(second_hash_payload)


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


def test_item_text_service_passes_owner_family_loot_culture_for_prompt():
    source_context = {
        "family_id": "bandit_gang",
        "clan_id": "clan-1",
        "owner_family": {
            "clan_id": "clan-1",
            "family_resource_id": "bandit_gang",
            "clan_name_ru": "Банда Воротной Щепы",
            "clan_description": "Разбойники держат пролом у старых ворот.",
            "archetype": "humanoid",
            "organization_type": "gang",
            "tags": ["human", "outlaw"],
            "loot_culture": {
                "craft_style": "грубая переделка найденных вещей",
                "craft_skill_hint": "не кузнецы; используют лом, двери, обшивку, ремни и гвозди",
                "salvage_sources": ["городские ворота", "разбитые двери"],
                "tone_hints": ["уличная практичность"],
                "equipment_origin_notes": ["щит может быть куском двери"],
            },
        },
    }
    request = ItemGenerationRequestDTO(
        base_id="shield",
        material_id="mat_oak_plank",
        rarity_tier=2,
        request_ai_text=True,
        source_context=source_context,
    )
    mechanical_item = ItemFactory().generate(request)

    payload = ItemTextService()._build_payload(mechanical_item, request)

    assert payload["source_context"]["owner_family"]["clan_name_ru"] == "Банда Воротной Щепы"
    assert payload["source_context"]["owner_family"]["loot_culture"]["salvage_sources"] == [
        "городские ворота",
        "разбитые двери",
    ]
