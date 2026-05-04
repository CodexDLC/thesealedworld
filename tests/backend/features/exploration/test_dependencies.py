from types import SimpleNamespace

import pytest
from starlette.datastructures import State

from src.backend.features.exploration.dependencies import build_exploration_service
from src.backend.features.exploration.services.exploration_service import ExplorationService


@pytest.mark.unit
def test_build_exploration_service_uses_registered_world_locations_state_key():
    state = State()
    state.character_sessions = object()
    state.world_locations = object()
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    service = build_exploration_service(request)  # type: ignore[arg-type]

    assert isinstance(service, ExplorationService)
    assert service._integrator.world_store is state.world_locations
