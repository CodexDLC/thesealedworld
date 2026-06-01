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
    "CombatModifiersDTO",
    "CharacterWorldStatsDTO",
    "FullModifiersDTO",
    "CharacterModifiersSaveDto",
]


_SHIELD_ADDITIONS = {"shield_guard_power", "shield_absorb_ratio", "shield_reflect_ratio"}

def test_ported_modifier_dto_defaults_match_runtime_contract() -> None:
    expected_overrides = {
        "main_hand_damage_spread": 0.1,
        "off_hand_damage_spread": 0.1,
        "item_damage_spread": 0.1,
        "main_hand_crit_cap": 0.75,
        "off_hand_crit_cap": 0.75,
        "item_crit_cap": 0.75,
        "magical_damage_spread": 0.1,
        "magical_crit_cap": 0.75,
        "dodge_cap": 0.75,
        "parry_cap": 0.50,
        "shield_block_cap": 0.75,
        "resistance_cap": 0.85,
        "shield_absorb_ratio": 0.40,
        "shield_reflect_ratio": 1.00,
        "shield_block_defense_weight": 1.0,
        "counter_attack_cap": 0.50,
        "pet_efficiency_mult": 1.0,
        "damage_mult": 1.0,
        "vampiric_trigger_cap": 1.0,
        "hand_size": 3,
    }
    for dto_name in LEGACY_PORTED_DTOS:
        current = getattr(modifiers, dto_name)().model_dump()
        expected = {field_name: expected_overrides.get(field_name, 0.0) for field_name in current}
        assert current == expected, f"DTO mismatch for {dto_name}"


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
