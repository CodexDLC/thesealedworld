from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.npc.services import NpcService


@pytest.mark.unit
async def test_npc_service_load_dialogue_context_flattens_state() -> None:
    repository = MagicMock()
    repository.get_or_create_state = AsyncMock(
        return_value=SimpleNamespace(
            reputation=4,
            affinity=2,
            flags={"met": True},
            counters={"meetings": 3},
        )
    )
    repository.commit = AsyncMock()
    service = NpcService(repository)

    context = await service.load_dialogue_context(character_id=7, npc_key="portal_pad_guide")

    assert context.definition.npc_key == "portal_pad_guide"
    assert context.flatten()["npc_flag_met"] == 1
    assert context.flatten()["npc_counter_meetings"] == 3


@pytest.mark.unit
async def test_npc_service_apply_effects_updates_state_and_is_idempotent() -> None:
    state = SimpleNamespace(
        reputation=0,
        affinity=0,
        flags={},
        counters={},
        version=1,
        last_interaction_at=None,
    )
    repository = MagicMock()
    repository.claim_effect_application = AsyncMock(side_effect=[True, False])
    repository.get_or_create_state = AsyncMock(return_value=state)
    repository.commit = AsyncMock()
    repository.rollback = AsyncMock()
    service = NpcService(repository)

    applied = await service.apply_effects(
        character_id=7,
        npc_key="portal_pad_guide",
        effects=[
            {"type": "npc.set_flag", "flag": "met", "value": True},
            {"type": "npc.bump_counter", "counter": "meetings", "amount": 1},
            {"type": "npc.adjust_reputation", "amount": 2},
        ],
        idempotency_key="abc",
    )
    duplicate = await service.apply_effects(
        character_id=7,
        npc_key="portal_pad_guide",
        effects=[{"type": "npc.set_flag", "flag": "met", "value": True}],
        idempotency_key="abc",
    )

    assert applied["applied"] is True
    assert applied["flags"]["met"] is True
    assert applied["counters"]["meetings"] == 1
    assert applied["reputation"] == 2
    assert duplicate["duplicate"] is True
