from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _use_bundled_default_combat_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMBAT_AI_POLICY_PATH", raising=False)
