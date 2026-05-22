from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.services.visual_regeneration_service import MonsterVisualRegenerationService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


@pytest.mark.unit
async def test_request_clan_family_images_enqueues_clan_and_member_images(monkeypatch: pytest.MonkeyPatch) -> None:
    clan = _clan_orm()
    member = _member_orm(clan)
    clan.members = [member]
    session = MagicMock()
    session.scalar = AsyncMock(return_value=clan)
    session.commit = AsyncMock()
    scheduler = SimpleNamespace(schedule_pending_task_ids=AsyncMock())
    service = MonsterVisualRegenerationService(session=session)

    async def fake_enqueue(prepared):
        assert [item.entity_type for item in prepared] == ["monster_clan", "monster_member"]
        return ["task-clan", "task-member"], scheduler

    monkeypatch.setattr(service, "_enqueue_prepared", fake_enqueue)

    result = await service.request_clan_family_images(str(clan.id))

    assert result.entity_type == "monster_clan_family"
    assert result.entity_id == str(clan.id)
    assert result.task_ids == ["task-clan", "task-member"]
    assert result.requested == 2
    assert clan.flavor_content["visual"]["status"] == "pending"
    assert member.generation_meta["visual"]["status"] == "pending"
    session.commit.assert_awaited_once()
    scheduler.schedule_pending_task_ids.assert_awaited_once()


@pytest.mark.unit
async def test_request_clan_images_enqueues_only_selected_clan_visuals(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _clan_orm()
    second = _clan_orm()
    result_rows = SimpleNamespace(all=lambda: [second, first])
    session = MagicMock()
    session.scalars = AsyncMock(return_value=result_rows)
    session.commit = AsyncMock()
    scheduler = SimpleNamespace(schedule_pending_task_ids=AsyncMock())
    service = MonsterVisualRegenerationService(session=session)

    async def fake_enqueue(prepared):
        assert [item.entity_id for item in prepared] == [str(first.id), str(second.id)]
        assert [item.entity_type for item in prepared] == ["monster_clan", "monster_clan"]
        return ["task-first", "task-second"], scheduler

    monkeypatch.setattr(service, "_enqueue_prepared", fake_enqueue)

    result = await service.request_clan_images([str(first.id), str(second.id)])

    assert result.entity_type == "monster_clans"
    assert result.entity_id is None
    assert result.task_ids == ["task-first", "task-second"]
    assert result.requested == 2
    assert all("monsters/generated/clans/" in key for key in result.storage_keys)
    session.commit.assert_awaited_once()
    scheduler.schedule_pending_task_ids.assert_awaited_once()


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
        unique_hash=str(uuid.uuid4()),
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
