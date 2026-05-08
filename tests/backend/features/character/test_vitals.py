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


def test_restore_to_max_vitals_refills_all_resources():
    attributes = CharacterSessionAttributesDTO(strength=15, endurance=16, mental=13)

    restored = CharacterVitalsCalculator.restore_to_max_vitals(attributes)

    assert restored.hp.cur == 64
    assert restored.hp.max == 64
    assert restored.energy.cur == 26
    assert restored.energy.max == 26
    assert restored.stamina.cur == 160
    assert restored.stamina.max == 160


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


def test_apply_regen_advances_damaged_resources_from_elapsed_time():
    vitals = CharacterSessionVitalsDTO(
        hp=VitalValueDTO(cur=20, max=100, regen=2.0),
        energy=VitalValueDTO(cur=5, max=20, regen=1.0),
        stamina=VitalValueDTO(cur=10, max=50, regen=4.0),
        last_update=100.0,
    )

    updated = CharacterVitalsCalculator.apply_regen(vitals, now=130.0)

    assert updated.hp.cur == 80
    assert updated.energy.cur == 20
    assert updated.stamina.cur == 50
    assert updated.last_update == 130.0


def test_apply_regen_keeps_fractional_time_when_no_integer_gain():
    vitals = CharacterSessionVitalsDTO(
        hp=VitalValueDTO(cur=20, max=100, regen=0.2),
        energy=VitalValueDTO(cur=20, max=20, regen=1.0),
        stamina=VitalValueDTO(cur=50, max=50, regen=1.0),
        last_update=100.0,
    )

    updated = CharacterVitalsCalculator.apply_regen(vitals, now=101.0)

    assert updated.hp.cur == 20
    assert updated.last_update == 100.0


def test_apply_regen_touches_full_vitals_to_prevent_idle_time_bank():
    vitals = CharacterSessionVitalsDTO(
        hp=VitalValueDTO(cur=100, max=100, regen=2.0),
        energy=VitalValueDTO(cur=20, max=20, regen=1.0),
        stamina=VitalValueDTO(cur=50, max=50, regen=1.0),
        last_update=100.0,
    )

    updated = CharacterVitalsCalculator.apply_regen(vitals, now=130.0)

    assert updated.hp.cur == 100
    assert updated.last_update == 130.0
