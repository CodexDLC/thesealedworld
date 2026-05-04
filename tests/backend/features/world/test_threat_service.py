import pytest

from src.backend.features.world.runtime.threat import ThreatService


@pytest.mark.unit
def test_threat_service_suppresses_anchor_tags_inside_d4_core():
    influence = ThreatService.describe(52, 52)

    assert influence.tier == 0
    assert influence.tags == []
    assert influence.is_inside_city_shield is True


@pytest.mark.unit
def test_threat_service_returns_anchor_pressure_outside_city():
    influence = ThreatService.describe(7, 7)

    assert influence.dominant_anchor == "north_prime"
    assert influence.biome_id == "stasis_wastes"
    assert influence.tier > 0
    assert influence.tags


@pytest.mark.unit
def test_threat_service_uses_hybrid_tags_between_anchors():
    influence = ThreatService.describe(7, 52)

    assert influence.dominant_anchor in {"north_prime", "west_prime"}
    assert any(tag in influence.tags for tag in ["hail_storm", "frozen_lightning", "shattering_sky"])
