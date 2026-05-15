from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO
from src.backend.features.monsters.resources.visuals import build_clan_visual
from src.backend.features.monsters.tasks_ai import (
    MONSTER_CLAN_IMAGE_TASK,
    MonsterClanImageTaskHandler,
    build_monster_clan_image_task_spec_from_orm,
)
from src.backend.infrastructure.monsters import GeneratedClanORM


def _clan_orm() -> GeneratedClanORM:
    visual = build_clan_visual(
        "rat_swarm",
        clan_name="Рой Черного Камня",
        description="Крысы держатся у влажных плит.",
        context_tags=["d4_rift_rat_king"],
    )
    return GeneratedClanORM(
        id=uuid.uuid4(),
        family_id="rat_swarm",
        tier=1,
        zone_id="D4_0_0",
        context_hash="context",
        unique_hash="unique",
        raw_tags={"season_id": "season-1"},
        flavor_content={"visual": visual},
        name_ru="Рой Черного Камня",
        description="Крысы держатся у влажных плит.",
    )


def test_monster_clan_image_spec_uses_visual_contract() -> None:
    clan = _clan_orm()

    spec = build_monster_clan_image_task_spec_from_orm(clan)

    assert spec.task_type == MONSTER_CLAN_IMAGE_TASK
    assert spec.output_kind == "image"
    assert spec.entity_id == str(clan.id)
    assert spec.asset_hash == clan.flavor_content["visual"]["asset_hash"]
    assert spec.storage_prefix == "monsters/generated/clans"
    assert spec.input_payload["visual"]["storage_key"] == clan.flavor_content["visual"]["storage_key"]


@pytest.mark.asyncio
async def test_monster_clan_image_handler_builds_provider_request_from_visual_payload() -> None:
    clan = _clan_orm()
    spec = build_monster_clan_image_task_spec_from_orm(clan)
    task = MagicMock(input_payload=spec.input_payload)
    handler = MonsterClanImageTaskHandler()

    request = await handler.build_request(task)

    assert request["kind"] == "image"
    assert request["content_type"] == "image/webp"
    assert request["storage_key"] == clan.flavor_content["visual"]["storage_key"]
    assert "Рой Черного Камня" in request["prompt"]
    assert "no text" in request["prompt"]


@pytest.mark.asyncio
async def test_monster_clan_image_handler_applies_generated_asset_to_clan_visual() -> None:
    clan = _clan_orm()
    session = MagicMock()
    session.scalar = AsyncMock(return_value=clan)
    session.flush = AsyncMock()
    handler = MonsterClanImageTaskHandler(session=session)
    task = MagicMock(entity_id=str(clan.id))

    await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(
            storage_key="monsters/generated/clans/hash.webp",
            generated_url="/static/generated-assets/monsters/generated/clans/hash.webp",
            asset_hash="hash",
            storage_backend="local",
            content_type="image/webp",
            size_bytes=123,
        ),
    )

    visual = clan.flavor_content["visual"]
    assert visual["status"] == "generated"
    assert visual["source"] == "ai_generated"
    assert visual["image_url"] == "/static/generated-assets/monsters/generated/clans/hash.webp"
    assert visual["storage_key"] == "monsters/generated/clans/hash.webp"
    assert visual["asset_hash"] == "hash"
    assert visual["content_type"] == "image/webp"
    assert visual["size_bytes"] == 123
    session.flush.assert_awaited_once()
