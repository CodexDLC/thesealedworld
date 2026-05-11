from temp.shared.schemas import modifier_dto as legacy

from src.backend.features.character.dto import modifiers

LEGACY_PORTED_DTOS = [
    "VitalsDTO",
    "CombatSkillsDTO",
    "SecondarySkillsDTO",
    "MainHandStatsDTO",
    "OffHandStatsDTO",
    "ItemStatsDTO",
    "PhysicalStatsDTO",
    "MagicalStatsDTO",
    "DefensiveStatsDTO",
    "MitigationStatsDTO",
    "ElementalStatsDTO",
    "StatusStatsDTO",
    "SpecialStatsDTO",
    "EnvironmentalStatsDTO",
    "SpeedStatsDTO",
    "CombatModifiersDTO",
    "CharacterWorldStatsDTO",
    "FullModifiersDTO",
    "CharacterModifiersSaveDto",
]


_SHIELD_ADDITIONS = {"shield_guard_power", "shield_absorb_ratio", "shield_reflect_ratio"}

_NEW_FIELDS_NOT_IN_LEGACY: dict[str, set[str]] = {
    # Fields added to MitigationStatsDTO after the legacy port (propagate to composite DTOs)
    "MitigationStatsDTO": _SHIELD_ADDITIONS,
    "CombatModifiersDTO": _SHIELD_ADDITIONS,
    "FullModifiersDTO": _SHIELD_ADDITIONS,
    "CharacterModifiersSaveDto": _SHIELD_ADDITIONS,
    "CharacterModifiersSaveDTO": _SHIELD_ADDITIONS,
}


def test_ported_modifier_dto_defaults_match_legacy_contract():
    for dto_name in LEGACY_PORTED_DTOS:
        current = getattr(modifiers, dto_name)().model_dump()
        expected = getattr(legacy, dto_name)().model_dump()
        extra = _NEW_FIELDS_NOT_IN_LEGACY.get(dto_name, set())
        current_filtered = {k: v for k, v in current.items() if k not in extra}
        assert current_filtered == expected, f"DTO mismatch for {dto_name}"


def test_combat_modifier_fields_match_legacy_contract():
    current = set(modifiers.CombatModifiersDTO.model_fields) - _SHIELD_ADDITIONS
    assert current == set(legacy.CombatModifiersDTO.model_fields)


def test_full_modifier_fields_match_legacy_contract():
    current = set(modifiers.FullModifiersDTO.model_fields) - _SHIELD_ADDITIONS
    assert current == set(legacy.FullModifiersDTO.model_fields)


def test_combat_modifier_blocks_cover_combat_modifier_dto_fields():
    block_fields: set[str] = set(modifiers.VitalsDTO.model_fields)
    for block in modifiers.COMBAT_MODIFIER_BLOCKS:
        block_fields.update(block.model_fields)

    assert block_fields == set(modifiers.CombatModifiersDTO.model_fields)


def test_modifier_dto_ignores_extra_runtime_keys():
    dto = modifiers.CombatModifiersDTO(main_hand_damage_base=12, unknown_runtime_key=99)

    assert dto.main_hand_damage_base == 12
    assert "unknown_runtime_key" not in dto.model_dump()


def test_legacy_save_alias_points_to_new_dto_name():
    assert modifiers.CharacterModifiersSaveDto is modifiers.CharacterModifiersSaveDTO
