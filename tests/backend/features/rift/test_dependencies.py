from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.backend.features.rift import dependencies
from src.backend.features.rift import events as rift_events
from src.backend.features.rift.services import RiftEntryService, RiftPlayerService


class SpyRiftRuntimeIntegration:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


@pytest.mark.unit
def test_rift_player_dependency_wires_membership_and_snapshot_repositories_for_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies, "RiftRuntimeIntegration", SpyRiftRuntimeIntegration)
    monkeypatch.setattr(dependencies, "get_mongo_provider", _fake_mongo_provider)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=object(), character_sessions=object())))
    db_session = object()

    service = dependencies.get_rift_player_service(request, db_session)  # type: ignore[arg-type]

    assert isinstance(service, RiftPlayerService)
    assert isinstance(service.runtime, SpyRiftRuntimeIntegration)
    assert service.runtime.kwargs["membership_repository"] is not None
    assert service.runtime.kwargs["snapshot_repository"] is not None
    assert service.runtime.kwargs["restore_lock"] is not None


@pytest.mark.unit
def test_rift_entry_dependency_wires_membership_and_snapshot_repositories_for_initial_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies, "RiftRuntimeIntegration", SpyRiftRuntimeIntegration)
    monkeypatch.setattr(dependencies, "get_mongo_provider", _fake_mongo_provider)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                redis=object(),
                character_sessions=object(),
                rift_population_bindings={},
            )
        )
    )
    db_session = object()

    service = dependencies.get_rift_entry_service(request, db_session)  # type: ignore[arg-type]

    assert isinstance(service, RiftEntryService)
    assert isinstance(service.runtime, SpyRiftRuntimeIntegration)
    assert service.runtime.kwargs["membership_repository"] is not None
    assert service.runtime.kwargs["snapshot_repository"] is not None
    assert service.runtime.kwargs["restore_lock"] is not None


@pytest.mark.unit
def test_rift_event_entry_service_wires_membership_and_snapshot_repositories_for_initial_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rift_events, "RiftRuntimeIntegration", SpyRiftRuntimeIntegration)
    monkeypatch.setattr(rift_events, "get_mongo_provider", _fake_mongo_provider)
    app = SimpleNamespace(
        state=SimpleNamespace(
            redis=object(),
            character_sessions=object(),
            rift_population_bindings={},
        )
    )
    db_session = object()

    service = rift_events._entry_service(app, db_session)  # type: ignore[arg-type]  # noqa: SLF001

    assert isinstance(service, RiftEntryService)
    assert isinstance(service.runtime, SpyRiftRuntimeIntegration)
    assert service.runtime.kwargs["membership_repository"] is not None
    assert service.runtime.kwargs["snapshot_repository"] is not None
    assert service.runtime.kwargs["restore_lock"] is not None


@pytest.mark.unit
def test_rift_dev_dependency_keeps_membership_and_snapshot_repositories_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies, "RiftRuntimeIntegration", SpyRiftRuntimeIntegration)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=object())))

    runtime = dependencies.get_rift_runtime_integration(request)  # type: ignore[arg-type]

    assert isinstance(runtime, SpyRiftRuntimeIntegration)
    assert runtime.kwargs["membership_repository"] is None
    assert runtime.kwargs["snapshot_repository"] is None
    assert runtime.kwargs["restore_lock"] is not None


def _fake_mongo_provider() -> Any:
    return SimpleNamespace(database=lambda: _FakeMongoDatabase())


class _FakeMongoDatabase(dict[str, Any]):
    def __missing__(self, key: str) -> Any:
        value = object()
        self[key] = value
        return value
