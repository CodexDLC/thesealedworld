from src.backend.features.game_catalog.combat.resources.effects.schemas import (
    EffectResistanceProfileDTO,
)

EFFECT_RESISTANCE_PROFILES: dict[str, EffectResistanceProfileDTO] = {
    "poison": EffectResistanceProfileDTO(
        profile_id="poison",
        target_modifiers=["poison_resistance", "debuff_avoidance"],
        source_modifiers=["control_chance_bonus"],
        tags=["poison", "dot"],
    ),
    "bleed": EffectResistanceProfileDTO(
        profile_id="bleed",
        target_modifiers=["bleed_resistance"],
        source_modifiers=["control_chance_bonus"],
        tags=["bleed", "dot"],
    ),
    "burn": EffectResistanceProfileDTO(
        profile_id="burn",
        target_modifiers=["fire_resistance", "debuff_avoidance"],
        source_modifiers=["control_chance_bonus"],
        tags=["burn", "fire", "dot"],
    ),
    "control_physical": EffectResistanceProfileDTO(
        profile_id="control_physical",
        target_modifiers=["control_resistance", "shock_resistance"],
        source_modifiers=["control_chance_bonus"],
        tags=["control", "physical"],
    ),
    "control_mental": EffectResistanceProfileDTO(
        profile_id="control_mental",
        target_modifiers=["mental_resistance", "control_resistance"],
        source_modifiers=["control_chance_bonus"],
        tags=["control", "mental"],
    ),
    "generic_debuff": EffectResistanceProfileDTO(
        profile_id="generic_debuff",
        target_modifiers=["debuff_avoidance"],
        source_modifiers=["control_chance_bonus"],
        tags=["debuff"],
    ),
}


def get_effect_resistance_profile(profile_id: str) -> EffectResistanceProfileDTO | None:
    return EFFECT_RESISTANCE_PROFILES.get(profile_id)
