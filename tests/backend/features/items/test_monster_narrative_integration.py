import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.integrations.monster_narrative import ItemMonsterNarrativeIntegration
from src.backend.infrastructure.monsters import GeneratedClanORM


@pytest.mark.unit
async def test_monster_narrative_integration_reads_new_generated_clan_shape() -> None:
    clan_id = uuid.uuid4()
    clan = GeneratedClanORM(
        id=clan_id,
        family_id="bandit_gang",
        identity_hash="identity",
        context_hash="context",
        context_identity={
            "biome_id": "city_ruins",
            "difficulty": "mid",
            "tags": ["rift", "roadside"],
            "habitat": {"biome": "city_ruins", "keys": ["broken_gate"]},
        },
        selected_traits=[],
        title="Банда Воротной Щепы",
        description="Разбойники держат пролом у старых ворот.",
        encounter_texts={"patrol": "Банда прочесывает дорогу."},
        generation_version=2,
        resource_version="1",
        metadata_={
            "flavor_content": {
                "loot_culture": {
                    "craft_style": "грубая переделка найденных вещей",
                    "craft_skill_hint": "используют лом, двери, ремни и гвозди",
                    "salvage_sources": ["городские ворота", "разбитые двери"],
                    "tone_hints": ["уличная практичность"],
                    "equipment_origin_notes": ["щит может быть куском двери"],
                }
            }
        },
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=clan)
    request = ItemGenerationRequestDTO(
        base_id="shield",
        rarity_tier=1,
        source_context={"clan_id": str(clan_id), "owner_family": {"clan_name_ru": "устаревшее имя"}},
    )

    result = await ItemMonsterNarrativeIntegration(session).enrich_request_from_db_clan(request)

    owner_family = result.source_context["owner_family"]
    assert owner_family["clan_name_ru"] == "Банда Воротной Щепы"
    assert owner_family["clan_description"] == "Разбойники держат пролом у старых ворот."
    assert owner_family["tags"] == ["rift", "roadside"]
    assert owner_family["habitat_keys"] == ["broken_gate"]
    assert owner_family["encounter_texts"]["patrol"] == "Банда прочесывает дорогу."
    assert owner_family["loot_culture"]["salvage_sources"] == ["городские ворота", "разбитые двери"]
