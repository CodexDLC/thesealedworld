from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PipelineMutationSource = Literal["weapon", "feint", "style", "effect", "ability", "monster", "system"]
PipelineMutationValueKind = Literal["bool", "int", "float", "str", "tuple_float"]


class PipelineMutationContractDTO(BaseModel):
    """Technical whitelist entry for one pipeline-local mutation."""

    id: str
    path: str
    value_kind: PipelineMutationValueKind
    default_value: Any = None
    allowed_sources: list[PipelineMutationSource] = Field(default_factory=list)


class PipelineMutationApplicationDTO(BaseModel):
    """Catalog-side request to apply a pipeline-local mutation."""

    mutation_id: str
    value_override: Any = None
    tags: list[str] = Field(default_factory=list)


def _contract(
    mutation_id: str,
    path: str,
    value_kind: PipelineMutationValueKind,
    default_value: Any,
    *,
    allowed_sources: tuple[PipelineMutationSource, ...] = (
        "weapon",
        "feint",
        "style",
        "effect",
        "ability",
        "monster",
        "system",
    ),
) -> PipelineMutationContractDTO:
    return PipelineMutationContractDTO(
        id=mutation_id,
        path=path,
        value_kind=value_kind,
        default_value=default_value,
        allowed_sources=list(allowed_sources),
    )


PIPELINE_MUTATION_CONTRACT_DEFINITIONS: tuple[PipelineMutationContractDTO, ...] = (
    # Phases.
    _contract("phase.run_pre_calc", "phases.run_pre_calc", "bool", True),
    _contract("phase.run_stats_engine", "phases.run_stats_engine", "bool", True),
    _contract("phase.run_calculator", "phases.run_calculator", "bool", True),
    _contract("phase.run_post_calc", "phases.run_post_calc", "bool", True),
    _contract("phase.is_target_dead", "phases.is_target_dead", "bool", False),
    # Force flags.
    _contract("force.hit", "flags.force.hit", "bool", True),
    _contract("force.miss", "flags.force.miss", "bool", True),
    _contract("force.crit", "flags.force.crit", "bool", True),
    _contract("force.dodge", "flags.force.dodge", "bool", True),
    _contract("force.parry", "flags.force.parry", "bool", True),
    _contract("force.block", "flags.force.block", "bool", True),
    _contract("ignore_miss", "flags.force.hit", "bool", True),
    _contract("ignore_evasion", "flags.force.hit_evasion", "bool", True),
    # Restrictions.
    _contract("cannot_crit", "flags.restriction.cannot_crit", "bool", True),
    _contract("ignore_parry", "flags.restriction.ignore_parry", "bool", True),
    _contract("ignore_block", "flags.restriction.ignore_block", "bool", True),
    # Mastery flags.
    _contract("mastery.light_armor", "flags.mastery.light_armor", "bool", True),
    _contract("mastery.medium_armor", "flags.mastery.medium_armor", "bool", True),
    _contract("mastery.shield_reflect", "flags.mastery.shield_reflect", "bool", True),
    _contract("mastery.unarmed_combo", "flags.mastery.unarmed_combo", "bool", True),
    # Formula flags.
    _contract("ignore_evasion_cap", "flags.formula.ignore_evasion_cap", "bool", True),
    _contract("zero_anti_evasion", "flags.formula.zero_anti_evasion", "bool", True),
    _contract("ignore_parry_cap", "flags.formula.ignore_parry_cap", "bool", True),
    _contract("ignore_block_cap", "flags.formula.ignore_block_cap", "bool", True),
    _contract("crit_ignore_anticrit", "flags.formula.crit_ignore_anticrit", "bool", True),
    _contract("crit_damage_boost", "flags.formula.crit_damage_boost", "bool", True),
    _contract("enable_pierce", "flags.formula.can_pierce", "bool", True),
    _contract("ignore_armor", "flags.formula.ignore_armor", "bool", True),
    _contract("ignore_flat_armor", "flags.formula.ignore_flat_armor", "bool", True),
    _contract("roll_flat_armor_ignore", "flags.formula.roll_flat_armor_ignore", "bool", True),
    _contract("boost_flat_armor_penetration", "flags.formula.boost_flat_armor_penetration", "bool", True),
    _contract("suppress_physical_resistance", "flags.formula.suppress_physical_resistance", "bool", True),
    _contract("ignore_physical_resistance", "flags.formula.ignore_physical_resistance", "bool", True),
    _contract("counter_chance_boost", "flags.formula.counter_chance_boost", "bool", True),
    # Damage type flags.
    _contract("damage.physical", "flags.damage.physical", "bool", True),
    _contract("damage.pure", "flags.damage.pure", "bool", True),
    _contract("damage.fire", "flags.damage.fire", "bool", True),
    _contract("damage.water", "flags.damage.water", "bool", True),
    _contract("damage.air", "flags.damage.air", "bool", True),
    _contract("damage.earth", "flags.damage.earth", "bool", True),
    _contract("damage.light", "flags.damage.light", "bool", True),
    _contract("damage.darkness", "flags.damage.darkness", "bool", True),
    _contract("damage.arcane", "flags.damage.arcane", "bool", True),
    _contract("damage.nature", "flags.damage.nature", "bool", True),
    _contract("damage.healing", "flags.damage.healing", "bool", True),
    # State flags.
    _contract("partial_absorb_reflect", "flags.state.partial_absorb_reflect", "bool", True),
    _contract("reflect_block_state", "flags.state.is_reflect_block", "bool", True),
    _contract("open_combo", "flags.state.open_combo", "bool", True),
    _contract("hit_index", "flags.state.hit_index", "int", 0),
    _contract("allow_counter_on_parry", "flags.state.allow_counter_on_parry", "bool", True),
    _contract("state.check_counter", "flags.state.check_counter", "bool", True),
    _contract("force_counter_on_dodge", "flags.state.force_counter_on_dodge", "bool", True),
    _contract("force_counter_on_parry", "flags.state.force_counter_on_parry", "bool", True),
    _contract("counter_to_cap_on_dodge", "flags.state.counter_to_cap_on_dodge", "bool", True),
    # Meta values. These are context routing knobs, not player-facing descriptions.
    _contract("meta.source_type", "flags.meta.source_type", "str", "main_hand"),
    _contract("meta.weapon_class", "flags.meta.weapon_class", "str", None),
    _contract("meta.crit_trigger_key", "flags.meta.crit_trigger_key", "str", None),
    _contract("meta.attack_index", "flags.meta.attack_index", "int", 0),
    _contract("meta.combo_stage", "flags.meta.combo_stage", "int", 0),
    _contract("meta.has_offhand_weapon", "flags.meta.has_offhand_weapon", "bool", True),
    _contract("meta.action_mode", "flags.meta.action_mode", "str", "exchange"),
    # Mechanics flags read outside the resolver.
    _contract("mechanics.pay_cost", "flags.mechanics.pay_cost", "bool", True),
    _contract("mechanics.grant_xp", "flags.mechanics.grant_xp", "bool", True),
    _contract("mechanics.check_death", "flags.mechanics.check_death", "bool", True),
    _contract("mechanics.apply_damage", "flags.mechanics.apply_damage", "bool", True),
    _contract("mechanics.apply_sustain", "flags.mechanics.apply_sustain", "bool", True),
    _contract("mechanics.apply_periodic", "flags.mechanics.apply_periodic", "bool", True),
    _contract("mechanics.generate_feints", "flags.mechanics.generate_feints", "bool", True),
    # Numeric pipeline-local modifiers.
    _contract("accuracy_mult", "mods.accuracy_mult", "float", 1.0),
    _contract("damage_mult", "mods.damage_mult", "float", 1.0),
    _contract("weapon_effect_value", "mods.weapon_effect_value", "float", 2.0),
    _contract("flat_armor_penetration_bonus_pct", "mods.flat_armor_penetration_bonus_pct", "float", 0.0),
    _contract("flat_armor_ignore_chance_bonus", "mods.flat_armor_ignore_chance_bonus", "float", 0.0),
    _contract("physical_resistance_suppression_pct", "mods.physical_resistance_suppression_pct", "float", 0.0),
    # Resolver stages.
    _contract("stage.check_accuracy", "stages.check_accuracy", "bool", True),
    _contract("stage.check_evasion", "stages.check_evasion", "bool", True),
    _contract("stage.check_parry", "stages.check_parry", "bool", True),
    _contract("stage.check_block", "stages.check_block", "bool", True),
    _contract("stage.check_crit", "stages.check_crit", "bool", True),
    _contract("stage.calculate_damage", "stages.calculate_damage", "bool", True),
    _contract("stage.calculate_healing", "stages.calculate_healing", "bool", True),
    _contract("stage.check_counter", "stages.check_counter", "bool", True),
    # Top-level exchange-local switches.
    _contract("override_damage", "override_damage", "tuple_float", None),
    _contract("can_counter", "can_counter", "bool", True),
    # Chain event commands. Cleave is intentionally excluded; target expansion belongs to collector/targeting.
    _contract("chain.trigger_offhand_attack", "result.chain_events.trigger_offhand_attack", "bool", True),
    _contract("chain.trigger_counter_attack", "result.chain_events.trigger_counter_attack", "bool", True),
    _contract("chain.trigger_extra_strike", "result.chain_events.trigger_extra_strike", "bool", True),
    _contract("chain.preserve_feint", "result.chain_events.preserve_feint", "bool", True),
)

PIPELINE_MUTATION_CONTRACTS: dict[str, PipelineMutationContractDTO] = {
    contract.id: contract for contract in PIPELINE_MUTATION_CONTRACT_DEFINITIONS
}

if len(PIPELINE_MUTATION_CONTRACTS) != len(PIPELINE_MUTATION_CONTRACT_DEFINITIONS):
    raise RuntimeError("Duplicate pipeline mutation contract id detected")


def get_pipeline_mutation_contract(mutation_id: str) -> PipelineMutationContractDTO | None:
    return PIPELINE_MUTATION_CONTRACTS.get(mutation_id)


def pipeline_mutation(mutation_id: str, value: Any = None) -> PipelineMutationApplicationDTO:
    return PipelineMutationApplicationDTO(mutation_id=mutation_id, value_override=value)
