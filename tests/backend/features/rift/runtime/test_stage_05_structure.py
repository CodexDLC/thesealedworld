from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.mark.unit
def test_rift_stage_05_runtime_modules_are_split_by_responsibility() -> None:
    modules = [
        "src.backend.features.rift.runtime.actions",
        "src.backend.features.rift.runtime.actions.dispatcher",
        "src.backend.features.rift.runtime.generation.canvas",
        "src.backend.features.rift.runtime.generation.chain",
        "src.backend.features.rift.runtime.generation.events",
        "src.backend.features.rift.runtime.generation.graph",
        "src.backend.features.rift.runtime.generation.placement",
        "src.backend.features.rift.runtime.generation.planner",
    ]

    for module_name in modules:
        importlib.import_module(module_name)


@pytest.mark.unit
def test_rift_actions_are_not_owned_by_screen_builder_monolith() -> None:
    source = Path("src/backend/features/rift/runtime/navigation/screen_builder.py").read_text(encoding="utf-8")

    assert "def resolve_rift_action_runtime" not in source
    assert "def _resolve_blocker_action" not in source
