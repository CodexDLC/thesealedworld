from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO
from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.tasks_ai import (
    MONSTER_CLAN_IMAGE_TASK,
    MONSTER_MEMBER_IMAGE_TASK,
    MonsterClanFlavorTaskHandler,
    MonsterClanImageTaskHandler,
    MonsterMemberImageTaskHandler,
    build_monster_clan_flavor_payload,
    build_monster_clan_image_task_spec_from_orm,
    build_monster_member_image_task_spec_from_orm,
)
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


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


def _member_orm(clan: GeneratedClanORM) -> GeneratedMonsterORM:
    visual = build_member_visual(
        "rat_swarm",
        variant_key="runner",
        role="minion",
        member_name="Каменная крыса",
        appearance="Мокрая крыса с темной шерстью.",
    )
    member = GeneratedMonsterORM(
        id=uuid.uuid4(),
        clan_id=clan.id,
        variant_key="runner",
        role="minion",
        member_tier=1,
        threat_rating=10,
        name_ru="Каменная крыса",
        description="Мокрая крыса с темной шерстью.",
        text_content={},
        scaled_attributes={},
        scaled_skills={},
        items={},
        vitals={},
        ai_profile={},
        generation_meta={"visual": visual},
    )
    member.clan = clan
    return member


def test_monster_clan_image_spec_uses_visual_contract() -> None:
    clan = _clan_orm()

    spec = build_monster_clan_image_task_spec_from_orm(clan)

    assert spec.task_type == MONSTER_CLAN_IMAGE_TASK
    assert spec.output_kind == "image"
    assert spec.entity_id == str(clan.id)
    assert spec.asset_hash == clan.flavor_content["visual"]["asset_hash"]
    assert spec.storage_prefix == "monsters/generated/clans"
    assert spec.input_payload["visual"]["storage_key"] == clan.flavor_content["visual"]["storage_key"]


def test_monster_clan_flavor_payload_includes_loot_culture_contract() -> None:
    payload = build_monster_clan_flavor_payload(
        family_id="bandit_gang",
        tier=2,
        raw_tags={"tags": ["city_ruins"], "biome_id": "city_ruins"},
        variant_ids=["bandit_knife_rat"],
    )

    assert payload["loot_culture_contract"]["purpose"]
    assert "loot_culture" in payload["text_contract"]["clan"]
    assert "location, biome, context tags, and rift profile" in payload["loot_culture_contract"]["must_reflect"]


@pytest.mark.asyncio
async def test_monster_clan_flavor_handler_builds_json_request_with_schema() -> None:
    task = MagicMock(
        input_payload=build_monster_clan_flavor_payload(
            family_id="rat_swarm",
            tier=1,
            raw_tags={"tags": ["d4_rift_rat_king"], "biome_id": "city_ruins"},
            variant_ids=["runner"],
        )
    )
    handler = MonsterClanFlavorTaskHandler()

    request = await handler.build_request(task)

    assert request["kind"] == "json"
    assert request["schema"].__name__ == "MonsterClanFlavorDTO"
    assert "rat_swarm" in request["prompt"].messages[1].content


@pytest.mark.asyncio
async def test_monster_clan_flavor_handler_applies_structured_json_and_returns_image_followups() -> None:
    clan = _clan_orm()
    member = _member_orm(clan)
    clan.members = [member]
    session = MagicMock()
    session.scalar = AsyncMock(return_value=clan)
    session.flush = AsyncMock()
    handler = MonsterClanFlavorTaskHandler(session=session)
    task = MagicMock(entity_id=str(clan.id))

    followups = await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(
            output_payload={
                "name_ru": "Стая Черного Камня",
                "description": "Крысы держатся у влажных плит.",
                "loot_culture": {
                    "craft_style": "собирают снаряжение из сырого мусора",
                    "craft_skill_hint": "тащат в гнездо все, что можно грызть и привязать",
                    "salvage_sources": ["ржавые решетки", "кости"],
                    "tone_hints": ["грязная сборка"],
                    "equipment_origin_notes": ["снаряжение пахнет сыростью"],
                },
                "variants_flavor": [
                    {
                        "variant_key": "runner",
                        "name": "Каменная крыса",
                        "appearance": "Мокрая крыса с темной шерстью.",
                        "detected": "Она замирает у плиты.",
                        "ambush": "Она бросается из темноты.",
                        "idle": "Она шевелит усами.",
                        "encounter": "Она замечает путника.",
                        "behavior": "Ищет слабое место.",
                    }
                ],
            }
        ),
    )

    assert clan.name_ru == "Стая Черного Камня"
    assert clan.flavor_content["loot_culture"]["craft_style"] == "собирают снаряжение из сырого мусора"
    assert member.name_ru == "Каменная крыса"
    assert followups[0].task_type == MONSTER_CLAN_IMAGE_TASK
    assert followups[1].task_type == MONSTER_MEMBER_IMAGE_TASK
    session.flush.assert_awaited_once()


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
    assert "No visible text" in request["prompt"]
    assert "no letters, no words, no numbers" in request["prompt"]


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


def test_monster_member_image_spec_uses_generation_meta_visual_contract() -> None:
    clan = _clan_orm()
    member = _member_orm(clan)

    spec = build_monster_member_image_task_spec_from_orm(member, clan=clan)

    assert spec.task_type == MONSTER_MEMBER_IMAGE_TASK
    assert spec.output_kind == "image"
    assert spec.entity_id == str(member.id)
    assert spec.asset_hash == member.generation_meta["visual"]["asset_hash"]
    assert spec.storage_prefix == "monsters/generated/members"
    assert spec.input_payload["visual"]["storage_key"] == member.generation_meta["visual"]["storage_key"]


@pytest.mark.asyncio
async def test_monster_member_image_handler_builds_provider_request_from_visual_payload() -> None:
    clan = _clan_orm()
    member = _member_orm(clan)
    spec = build_monster_member_image_task_spec_from_orm(member, clan=clan)
    task = MagicMock(input_payload=spec.input_payload)
    handler = MonsterMemberImageTaskHandler()

    request = await handler.build_request(task)

    assert request["kind"] == "image"
    assert request["content_type"] == "image/webp"
    assert request["storage_key"] == member.generation_meta["visual"]["storage_key"]
    assert "Каменная крыса" in request["prompt"]
    assert "monster_member_template" in request["prompt"]
    assert "exactly one individual" in request["prompt"]
    assert "Do not render a pack" in request["prompt"]
    assert "No visible text" in request["prompt"]
    assert "no letters, no words, no numbers" in request["prompt"]


@pytest.mark.asyncio
async def test_monster_member_image_handler_applies_generated_asset_to_member_visual() -> None:
    clan = _clan_orm()
    member = _member_orm(clan)
    session = MagicMock()
    session.scalar = AsyncMock(return_value=member)
    session.flush = AsyncMock()
    handler = MonsterMemberImageTaskHandler(session=session)
    task = MagicMock(entity_id=str(member.id))

    await handler.apply_result(
        task,
        AIGenerationTaskResultDTO(
            storage_key="monsters/generated/members/hash.png",
            generated_url="/static/generated-assets/monsters/generated/members/hash.png",
            asset_hash="hash",
            storage_backend="local",
            content_type="image/png",
            size_bytes=456,
        ),
    )

    visual = member.generation_meta["visual"]
    assert visual["status"] == "generated"
    assert visual["source"] == "ai_generated"
    assert visual["image_url"] == "/static/generated-assets/monsters/generated/members/hash.png"
    assert visual["storage_key"] == "monsters/generated/members/hash.png"
    assert visual["asset_hash"] == "hash"
    assert visual["content_type"] == "image/png"
    assert visual["size_bytes"] == 456
    session.flush.assert_awaited_once()
