from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.npc.integrations import NpcIntegration


@pytest.mark.unit
async def test_npc_integration_exposes_scenario_safe_operations() -> None:
    service = MagicMock()
    service.load_dialogue_context = AsyncMock(return_value=SimpleNamespace(reputation=1))
    service.apply_effects = AsyncMock(return_value={"applied": True})
    service.get_or_create_state = AsyncMock(return_value=SimpleNamespace(flags={"met": True}))
    integration = NpcIntegration(service)

    context = await integration.load_dialogue_context(character_id=7, npc_key="portal_pad_guide")
    effects = await integration.apply_effects(
        character_id=7,
        npc_key="portal_pad_guide",
        effects=[{"type": "npc.set_flag", "flag": "met"}],
        idempotency_key="scenario:test",
    )
    state = await integration.get_or_create_state(character_id=7, npc_key="portal_pad_guide")

    assert context.reputation == 1
    assert effects == {"applied": True}
    assert state.flags["met"] is True


def test_other_backend_features_do_not_import_npc_internal_layers() -> None:
    root = Path("src/backend/features")
    offenders: list[str] = []
    forbidden = (
        "src.backend.features.npc.services",
        "src.backend.features.npc.repositories",
    )

    for path in root.rglob("*.py"):
        if path.parts[:4] == ("src", "backend", "features", "npc"):
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden):
            offenders.append(path.as_posix())

    assert offenders == []
