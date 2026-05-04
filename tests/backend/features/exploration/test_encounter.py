# tests/backend/features/exploration/test_encounter.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.features.exploration.runtime.encounter import EncounterEngine
from src.shared.schemas.exploration import EncounterType, DetectionStatus

@pytest.mark.asyncio
async def test_encounter_safe_zone():
    engine = EncounterEngine()
    location_data = {"flags": {"is_safe_zone": True}}

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data=location_data,
        scouting_skill=10.0
    )

    assert encounter is None


@pytest.mark.asyncio
async def test_encounter_city_shield_threat_zero_is_safe_even_with_stale_flag():
    engine = EncounterEngine()
    location_data = {
        "flags": {
            "is_safe_zone": False,
            "threat_tier": 0,
            "anchor_influence": {"is_inside_city_shield": True},
        }
    }

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data=location_data,
        scouting_skill=0.0,
        trigger="move",
        loc_id="52_50",
    )

    assert encounter is None

@pytest.mark.asyncio
async def test_encounter_combat_generation():
    # Mock events and chance service to force combat
    mock_events = MagicMock()
    mock_events.create_combat_session = AsyncMock(return_value="test_session_id")

    engine = EncounterEngine(events=mock_events)

    # We need to mock ChanceService.check_chance within the engine's context
    # Since it's a static method, we can patch it
    from src.backend.core.calculators.chance_service import ChanceService

    # Force combat chance to succeed, others to fail
    def side_effect(percent):
        if percent > 0.1: # CHANCE_COMBAT_BASE is 0.45
            return True
        return False

    ChanceService.check_chance = MagicMock(side_effect=side_effect)

    location_data = {"flags": {"is_safe_zone": False, "threat_tier": 1}}

    encounter = await engine.try_generate_encounter(
        char_id=1,
        location_data=location_data,
        scouting_skill=100.0, # High skill for DETECTED status
        loc_id="50_50"
    )

    assert encounter is not None
    assert encounter.type == EncounterType.COMBAT
    assert encounter.session_id == "test_session_id"
    assert encounter.status == DetectionStatus.DETECTED
