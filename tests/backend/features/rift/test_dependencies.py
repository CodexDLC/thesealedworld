from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.backend.features.rift import dependencies
from src.backend.features.rift.services import RiftPlayerService


class SpyRiftRuntimeIntegration:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


@pytest.mark.unit
def test_rift_player_dependency_wires_db_state_repositories_for_cold_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "RiftRuntimeIntegration", SpyRiftRuntimeIntegration)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=object(), character_sessions=object())))
    db_session = object()

    service = dependencies.get_rift_player_service(request, db_session)  # type: ignore[arg-type]

    assert isinstance(service, RiftPlayerService)
    assert isinstance(service.runtime, SpyRiftRuntimeIntegration)
    assert service.runtime.kwargs["portal_key_repository"] is not None
    assert service.runtime.kwargs["instance_state_repository"] is not None
    assert service.runtime.kwargs["run_state_repository"] is not None


@pytest.mark.unit
def test_rift_dev_dependency_keeps_db_state_repositories_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "RiftRuntimeIntegration", SpyRiftRuntimeIntegration)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=object())))

    runtime = dependencies.get_rift_runtime_integration(request)  # type: ignore[arg-type]

    assert isinstance(runtime, SpyRiftRuntimeIntegration)
    assert runtime.kwargs["portal_key_repository"] is None
    assert runtime.kwargs["instance_state_repository"] is None
    assert runtime.kwargs["run_state_repository"] is None
