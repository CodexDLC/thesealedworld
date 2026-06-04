from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.services.visual_regeneration_service import MonsterVisualRegenerationService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


@pytest.mark.unit
async def test_request_clan_member_images_enqueues_only_member_images(monkeypatch: pytest.MonkeyPatch) -> None:
    clan = _clan_orm()
    member = _member_orm(clan)
    clan.members = [member]
    session = MagicMock()
    session.scalar = AsyncMock(return_value=clan)
    session.commit = AsyncMock()
    scheduler = SimpleNamespace(schedule_pending_task_ids=AsyncMock())
    service = MonsterVisualRegenerationService(session=session)

    async def fake_enqueue(prepared):
        assert [item.entity_type for item in prepared] == ["monster_member"]
        return ["task-member"], scheduler

    monkeypatch.setattr(service, "_enqueue_prepared", fake_enqueue)

    result = await service.request_clan_member_images(str(clan.id))

    assert result.entity_type == "monster_clan_members"
    assert result.entity_id == str(clan.id)
    assert result.task_ids == ["task-member"]
    assert result.requested == 1
    assert clan.metadata_["visual"]["status"] == "placeholder"
    assert member.metadata_["visual"]["status"] == "pending"
    assert "monsters/generated/members/" in result.storage_keys[0]
    session.commit.assert_awaited_once()
    scheduler.schedule_pending_task_ids.assert_awaited_once()


@pytest.mark.unit
async def test_request_clan_member_images_for_clans_enqueues_selected_member_visuals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _clan_orm()
    second = _clan_orm()
    first.members = [_member_orm(first)]
    second.members = [_member_orm(second)]
    result_rows = SimpleNamespace(all=lambda: [second, first])
    session = MagicMock()
    session.scalars = AsyncMock(return_value=result_rows)
    session.commit = AsyncMock()
    scheduler = SimpleNamespace(schedule_pending_task_ids=AsyncMock())
    service = MonsterVisualRegenerationService(session=session)

    async def fake_enqueue(prepared):
        assert [item.entity_type for item in prepared] == ["monster_member", "monster_member"]
        return ["task-first", "task-second"], scheduler

    monkeypatch.setattr(service, "_enqueue_prepared", fake_enqueue)

    result = await service.request_clan_member_images_for_clans([str(first.id), str(second.id)])

    assert result.entity_type == "monster_clan_members"
    assert result.entity_id is None
    assert result.task_ids == ["task-first", "task-second"]
    assert result.requested == 2
    assert all("monsters/generated/members/" in key for key in result.storage_keys)
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
        identity_hash=str(uuid.uuid4()),
        context_identity={"season_id": "season-1", "tags": ["d4_rift_rat_king"], "tier": 1},
        context_hash="context",
        selected_traits=[],
        title="Рой Черного Камня",
        description="Крысы держатся у влажных плит.",
        encounter_texts={},
        generation_version=2,
        resource_version="1",
        metadata_={"visual": visual},
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
        variant_id="runner",
        member_hash="runner",
        role="minion",
        title="Каменная крыса",
        short_description="Мокрая крыса с темной шерстью.",
        min_tier=1,
        max_tier=1,
        mongo_actor_key=f"actor:{clan.id}:runner",
        metadata_={"visual": visual},
    )
    member.clan = clan
    return member
