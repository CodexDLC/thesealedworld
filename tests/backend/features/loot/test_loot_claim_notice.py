from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.backend.features.loot.workers.tasks import loot_claim_task as task_module


class FakeRedis:
    def __init__(self) -> None:
        self.xadds: list[tuple[str, Any]] = []

    async def xadd(self, stream: str, fields: Any, **kwargs: Any) -> None:
        self.xadds.append((stream, fields))


@pytest.mark.asyncio
async def test_loot_claim_emits_claimed_items_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_module, "_transfer_to_inventory", AsyncMock(return_value=True))
    monkeypatch.setattr(task_module, "LootManager", lambda *_a, **_k: object())
    integration = SimpleNamespace(mark_items_claimed=AsyncMock(return_value=SimpleNamespace(is_empty=False)))
    monkeypatch.setattr(task_module, "LootIntegration", lambda *_a, **_k: integration)

    redis_client = FakeRedis()
    ctx = {
        "redis_service": object(),
        "redis_client_internal": redis_client,
    }
    payload = {
        "char_id": 42,
        "corpse_id": "corpse-1",
        "instance_ids": ["i1"],
        "resource_deltas": {},
        "summary_items": ["Ржавый клинок"],
    }

    await task_module.loot_claim_task(ctx, payload)

    assert len(redis_client.xadds) == 1
    _, encoded = redis_client.xadds[0]
    assert "player.notice" in str(encoded)
    assert encoded["template_key"] == "loot.items_claimed"
    assert json.loads(encoded["variables"]) == {"summary": "Ржавый клинок"}


@pytest.mark.asyncio
async def test_loot_claim_batch_emits_one_notice_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_module, "_transfer_to_inventory", AsyncMock(return_value=True))
    monkeypatch.setattr(task_module, "LootManager", lambda *_a, **_k: object())
    integration = SimpleNamespace(mark_items_claimed=AsyncMock(return_value=SimpleNamespace(is_empty=True)))
    monkeypatch.setattr(task_module, "LootIntegration", lambda *_a, **_k: integration)

    redis_client = FakeRedis()
    ctx = {
        "redis_service": object(),
        "redis_client_internal": redis_client,
    }
    payload = {
        "char_id": 42,
        "claims": [
            {
                "corpse_id": "corpse-1",
                "instance_ids": ["i1"],
                "resource_deltas": {"coin_copper": 3},
                "summary_items": ["Ржавый клинок", "Медные монеты x3"],
            },
            {
                "corpse_id": "corpse-2",
                "instance_ids": [],
                "resource_deltas": {"coin_copper": 3},
                "summary_items": ["Медные монеты x3"],
            },
        ],
    }

    await task_module.loot_claim_task(ctx, payload)

    assert task_module._transfer_to_inventory.await_count == 2
    assert integration.mark_items_claimed.await_count == 2
    assert len(redis_client.xadds) == 1
    _, encoded = redis_client.xadds[0]
    assert encoded["template_key"] == "loot.items_claimed"
    assert json.loads(encoded["variables"]) == {"summary": "Ржавый клинок, Медные монеты x6"}


@pytest.mark.asyncio
async def test_loot_claim_no_notice_when_transfer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_module, "_transfer_to_inventory", AsyncMock(return_value=False))
    redis_client = FakeRedis()
    ctx = {"redis_service": object(), "redis_client_internal": redis_client}
    payload = {"char_id": 42, "corpse_id": "corpse-1", "instance_ids": ["i1"], "resource_deltas": {}}

    with pytest.raises(RuntimeError):
        await task_module.loot_claim_task(ctx, payload)

    assert redis_client.xadds == []
