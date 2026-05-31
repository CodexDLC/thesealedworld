from __future__ import annotations

import time
from typing import Any

import pytest

from src.backend.features.loot.integrations.loot_integration import ITEMS_GENERATE_REQUESTED, LootIntegration
from src.shared.schemas.loot import ClaimResultDTO, CorpseDTO, LootItemDTO, LootTimestamps


class FakeEvents:
    def __init__(self) -> None:
        self.calls = []

    async def request(self, event: str, payload: dict, timeout: float):
        self.calls.append((event, payload, timeout))
        return {"status": "ok", "item_ids": ["item-1"]}


class _RecordingManager:
    def __init__(self) -> None:
        self.save_calls: list[tuple[Any, str, Any]] = []
        self.patch_calls: list[tuple[str, dict[str, Any]]] = []
        self.ttl_calls: list[tuple[str, Any]] = []

    async def save_corpse(self, corpse: Any, location_id: str, ttl: int) -> None:
        self.save_calls.append((corpse, location_id, ttl))

    async def patch_corpse(self, corpse_id: str, fields: dict[str, Any]) -> None:
        self.patch_calls.append((corpse_id, fields))

    async def set_ttl(self, corpse_id: str, seconds: int) -> None:
        self.ttl_calls.append((corpse_id, seconds))

    async def remove_items_from_corpse(self, corpse_id: str, instance_ids, resource_template_ids):
        return CorpseDTO(
            id=corpse_id,
            monster_name="Wolf",
            items=[],
            timestamps=LootTimestamps(created_at=time.time()),
        )


class _FakeGameConfig:
    """Reproduces a misconfigured cabinet override where TTLs leaked into Redis as floats."""

    async def get_int(self, namespace: str, key: str, default: int) -> int:
        # Simulate cabinet returning a sane integer.
        return int(default)


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_corpse_passes_integer_ttl_when_game_config_is_used() -> None:
    """Regression: float TTLs are rejected by Redis EXPIRE — must always be int."""
    manager = _RecordingManager()
    integration = LootIntegration(manager=manager, game_config=_FakeGameConfig())  # type: ignore[arg-type]

    corpse = CorpseDTO(monster_name="Wolf", items=[], timestamps=LootTimestamps(created_at=time.time()))
    await integration.persist_corpse(corpse, location_id="forest")

    assert manager.save_calls, "save_corpse should have been called"
    _, _, ttl = manager.save_calls[0]
    assert isinstance(ttl, int), f"persist_corpse must pass int TTL, got {type(ttl).__name__}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_activate_corpses_passes_integer_ttl() -> None:
    manager = _RecordingManager()
    integration = LootIntegration(manager=manager, game_config=_FakeGameConfig())  # type: ignore[arg-type]

    await integration.activate_corpses(["corpse-1"], char_ids=[42], location_id="forest")

    assert manager.patch_calls, "patch_corpse should have been called"
    assert manager.ttl_calls, "set_ttl should have been called for activated corpse"
    _, seconds = manager.ttl_calls[0]
    assert isinstance(seconds, int), (
        f"activate_corpses must compute int TTL, got {type(seconds).__name__}={seconds}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_items_claimed_passes_integer_empty_ttl() -> None:
    manager = _RecordingManager()
    integration = LootIntegration(manager=manager, game_config=_FakeGameConfig())  # type: ignore[arg-type]

    await integration.mark_items_claimed(
        "corpse-1",
        ClaimResultDTO(instance_ids=[], resource_deltas={}),
    )

    assert manager.ttl_calls, "set_ttl should have been called for empty corpse"
    _, seconds = manager.ttl_calls[0]
    assert isinstance(seconds, int), f"set_ttl must receive int seconds, got {type(seconds).__name__}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_corpse_coerces_float_override_from_misconfigured_cabinet() -> None:
    """Even if cabinet leaks a float through (e.g. old data), integration must coerce."""

    class _FloatLeakingConfig:
        async def get_int(self, namespace: str, key: str, default: int) -> Any:  # noqa: D401
            return 86400.0  # legacy float override

    manager = _RecordingManager()
    integration = LootIntegration(manager=manager, game_config=_FloatLeakingConfig())  # type: ignore[arg-type]

    corpse = CorpseDTO(monster_name="Wolf", items=[], timestamps=LootTimestamps(created_at=time.time()))
    await integration.persist_corpse(corpse, location_id="forest")

    _, _, ttl = manager.save_calls[0]
    assert isinstance(ttl, int)


# Silence unused-import lint when LootItemDTO is not referenced.
_ = LootItemDTO
