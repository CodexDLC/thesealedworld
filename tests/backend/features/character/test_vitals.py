from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionVitalsDTO,
    VitalValueDTO,
)


def test_initial_vitals_fill_current_from_calculated_maximums():
    attributes = CharacterSessionAttributesDTO(strength=15, endurance=16, mental=13)

    vitals = CharacterVitalsCalculator.build_initial_vitals(attributes)

    assert vitals.hp.max == 64
    assert vitals.hp.cur == 64
    assert vitals.energy.max == 26
    assert vitals.energy.cur == 26
    assert vitals.stamina.max == 160
    assert vitals.stamina.cur == 160
    assert vitals.hp.regen == 8.0
    assert vitals.energy.regen == 6.5
    assert vitals.stamina.regen == 3.2


def test_refresh_max_vitals_preserves_current_values_from_combat():
    attributes = CharacterSessionAttributesDTO(strength=15, endurance=16, mental=13)
    current = CharacterSessionVitalsDTO(
        hp=VitalValueDTO(cur=42, max=100),
        energy=VitalValueDTO(cur=25, max=100),
        stamina=VitalValueDTO(cur=12, max=100),
    )

    refreshed = CharacterVitalsCalculator.refresh_max_vitals(current, attributes)

    assert refreshed.hp.cur == 42
    assert refreshed.hp.max == 64
    assert refreshed.energy.cur == 25
    assert refreshed.energy.max == 26
    assert refreshed.stamina.cur == 12
    assert refreshed.stamina.max == 160


def test_refresh_max_vitals_clamps_current_values_to_new_maximums():
    attributes = CharacterSessionAttributesDTO(strength=8, endurance=8, mental=8)
    current = CharacterSessionVitalsDTO(
        hp=VitalValueDTO(cur=999, max=100),
        energy=VitalValueDTO(cur=999, max=100),
        stamina=VitalValueDTO(cur=999, max=100),
    )

    refreshed = CharacterVitalsCalculator.refresh_max_vitals(current, attributes)

    assert refreshed.hp.cur == 32
    assert refreshed.energy.cur == 16
    assert refreshed.stamina.cur == 80


def test_snapshot_restore_uses_saved_current_values_with_recalculated_maximums():
    attributes = CharacterSessionAttributesDTO(strength=15, endurance=16, mental=13)
    snapshot = {
        "hp": {"cur": 41, "max": 100, "regen": 0.0},
        "energy": {"cur": 22, "max": 100, "regen": 0.0},
        "stamina": {"cur": 15, "max": 100, "regen": 0.0},
        "last_update": 123.0,
    }

    vitals = CharacterVitalsCalculator.build_vitals_from_snapshot(snapshot, attributes)

    assert vitals.hp.cur == 41
    assert vitals.hp.max == 64
    assert vitals.energy.cur == 22
    assert vitals.energy.max == 26
    assert vitals.stamina.cur == 15
    assert vitals.stamina.max == 160
    assert vitals.last_update == 123.0
