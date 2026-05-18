from __future__ import annotations

import pytest

from src.backend.features.loot.integrations.loot_integration import ITEMS_GENERATE_REQUESTED, LootIntegration


class FakeEvents:
    def __init__(self) -> None:
        self.calls = []

    async def request(self, event: str, payload: dict, timeout: float):
        self.calls.append((event, payload, timeout))
        return {"status": "ok", "item_ids": ["item-1"]}


@pytest.mark.unit
async def test_loot_item_instance_requests_ai_text_for_template_cache() -> None:
    events = FakeEvents()
    integration = LootIntegration(manager=None, events=events)

    item_id = await integration.request_item_instance(
        base_id="warhammer",
        tier=2,
        source_context={"monster_family_id": "bandit_gang", "member_role": "bruiser", "member_tier": 2},
    )

    assert item_id == "item-1"
    event, payload, timeout = events.calls[0]
    assert event == ITEMS_GENERATE_REQUESTED
    assert timeout == 15.0
    assert payload["request_ai_text"] is True
    assert payload["source_context"]["monster_family_id"] == "bandit_gang"
