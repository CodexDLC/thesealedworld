from __future__ import annotations

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
async def test_loot_claim_emits_corpse_searched_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_module, "_transfer_to_inventory", AsyncMock(return_value=True))
    monkeypatch.setattr(task_module, "LootManager", lambda *_a, **_k: object())
    integration = SimpleNamespace(mark_items_claimed=AsyncMock(return_value=SimpleNamespace(is_empty=False)))
    monkeypatch.setattr(task_module, "LootIntegration", lambda *_a, **_k: integration)

    redis_client = FakeRedis()
    ctx = {
        "redis_service": object(),
        "redis_client_internal": redis_client,
    }
    payload = {"char_id": 42, "corpse_id": "corpse-1", "instance_ids": ["i1"], "resource_deltas": {}}

    await task_module.loot_claim_task(ctx, payload)

    assert len(redis_client.xadds) == 1
    _, encoded = redis_client.xadds[0]
    assert "player.notice" in str(encoded)
    assert "loot.corpse_searched" in str(encoded)


@pytest.mark.asyncio
async def test_loot_claim_no_notice_when_transfer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_module, "_transfer_to_inventory", AsyncMock(return_value=False))
    redis_client = FakeRedis()
    ctx = {"redis_service": object(), "redis_client_internal": redis_client}
    payload = {"char_id": 42, "corpse_id": "corpse-1", "instance_ids": ["i1"], "resource_deltas": {}}

    with pytest.raises(RuntimeError):
        await task_module.loot_claim_task(ctx, payload)

    assert redis_client.xadds == []
