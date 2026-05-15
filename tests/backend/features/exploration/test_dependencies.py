from types import SimpleNamespace

import pytest
from starlette.datastructures import State

from src.backend.features.exploration.dependencies import build_exploration_gateway, build_exploration_service
from src.backend.features.exploration.gateway import ExplorationGateway
from src.backend.features.exploration.services.exploration_service import ExplorationService


@pytest.mark.unit
def test_build_exploration_service_uses_registered_world_locations_state_key():
    state = State()
    state.character_sessions = object()
    state.world_locations = object()
    state.redis_managers = SimpleNamespace(expeditions=object())
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    service = build_exploration_service(request, object())  # type: ignore[arg-type]

    assert isinstance(service, ExplorationService)
    assert service._integrator.world_store is state.world_locations


@pytest.mark.unit
def test_build_exploration_gateway_uses_registered_world_locations_state_key():
    state = State()
    state.character_sessions = object()
    state.world_locations = object()
    state.redis = object()
    state.events = object()
    state.redis_managers = SimpleNamespace(expeditions=object())
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    gateway = build_exploration_gateway(request, object())  # type: ignore[arg-type]

    assert isinstance(gateway, ExplorationGateway)
    assert gateway._navigation._integrator.world_store is state.world_locations
