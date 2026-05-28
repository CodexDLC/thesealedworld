from __future__ import annotations

import pytest

from src.backend.features.rift.api.router import build_rift_router, router


@pytest.mark.unit
def test_dev_rift_router_exposes_rebuild_endpoint_without_blocker_route() -> None:
    paths = {route.path for route in router.routes}

    assert "/api/game/rift/{char_id}/view" in paths
    assert "/api/game/rift/{char_id}/leave" in paths
    assert "/api/game/rift/{char_id}/complete" in paths
    assert "/api/dev/rift/{rift_instance_id}/rebuild" in paths
    assert "/api/dev/rift/{rift_instance_id}/travel/start" in paths
    assert "/api/dev/rift/{rift_instance_id}/travel/tick" in paths
    assert "/api/dev/rift/{rift_instance_id}/action" in paths
    assert "/api/dev/rift/{rift_instance_id}/combat/resolve" not in paths
    assert "/api/dev/rift/{rift_instance_id}/node-event/resolve" not in paths
    assert "/api/dev/rift/{rift_instance_id}/move" not in paths
    assert "/api/dev/rift/{rift_instance_id}/reroll-blockers" not in paths


@pytest.mark.unit
def test_dev_rift_router_can_be_disabled_for_production() -> None:
    paths = {route.path for route in build_rift_router(enable_dev_routes=False).routes}

    assert "/api/game/rift/{char_id}/view" in paths
    assert "/api/dev/rift/starter-rift/start" not in paths
    assert "/api/dev/rift/{rift_instance_id}/rebuild" not in paths
