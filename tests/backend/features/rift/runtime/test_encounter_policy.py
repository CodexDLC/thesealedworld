from src.backend.features.rift.runtime.encounter import composition_policy_for_encounter_kind


def test_rift_encounter_policy_limits_ordinary_kinds_to_minion_pressure() -> None:
    assert composition_policy_for_encounter_kind(None) is None
    assert composition_policy_for_encounter_kind("ordinary") == {"encounter_kind": "ordinary"}
    assert composition_policy_for_encounter_kind("transition") == {"encounter_kind": "ordinary"}


def test_rift_encounter_policy_returns_structural_rules_for_special_kinds() -> None:
    heart_guard = composition_policy_for_encounter_kind("heart_guard")
    boss_solo = composition_policy_for_encounter_kind("boss_solo")

    assert heart_guard == {"encounter_kind": "boss"}
    assert boss_solo == {
        "encounter_kind": "boss",
        "allowed_roles": ["boss"],
        "required_roles": ["boss"],
        "min_units": 1,
        "max_units": 1,
        "allow_repeated_members": False,
    }


def test_rift_encounter_policy_returns_copy() -> None:
    first = composition_policy_for_encounter_kind("boss_solo")
    second = composition_policy_for_encounter_kind("boss_solo")
    assert first is not None
    assert second is not None

    first["allowed_roles"].append("minion")

    assert second["allowed_roles"] == ["boss"]
