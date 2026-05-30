"""Damage trace + HIT event emission."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatEventDTO

from ...support import trace_writer

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO

    from ._state import DamageState


def emit(
    state: DamageState,
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
) -> None:
    trace_writer.trace_damage(
        res,
        raw=state.raw_damage,
        final=state.total_damage,
        min_d=state.min_d,
        max_d=state.max_d,
        base=state.base,
        spread=state.spread,
        parts=state.damage_parts,
        armor=getattr(def_.mods, "armor", 0.0),
        magic_armor=state.magic_armor_flat,
        shield_absorb=state.shield_absorb,
        shield_absorb_cap=state.shield_absorb_cap,
        shield_absorb_ratio=state.shield_absorb_ratio,
        shield_guard_power=state.shield_guard_power,
        shield_block_branch=res.shield_block_branch,
        shield_reflect=state.shield_reflect,
        shield_reflect_base=state.shield_reflect_base,
        shield_reflect_ratio=state.shield_reflect_ratio,
        shield_mastery=state.shield_mastery,
        weapon_technique_bonus_damage=ctx.mods.weapon_technique_bonus_damage,
        phys_res=state.phys_res_raw,
        physical_suppression=state.phys_suppression,
        physical_resistance_suppression=state.phys_res_suppression_pct,
        effective_phys_res=state.mitigation_pct,
        crit_mult=state.crit_multiplier,
        dbp={
            "base": state.base_before_physical,
            "weapon": getattr(atk.mods, "physical_damage", 0.0) if ctx.flags.damage.physical else 0.0,
            "bonus": getattr(atk.mods, "physical_damage_bonus", 0.0) if ctx.flags.damage.physical else 0.0,
            "added": state.physical_added,
            "raw_roll": state.raw_damage,
        },
        resl={
            "raw": state.phys_res_raw,
            "effective": state.mitigation_pct,
            "suppression": state.phys_suppression,
            "suppression_pct": state.phys_res_suppression_pct,
            "after": state.after_resist,
        },
        arm=state.armor_trace,
        after_resist=state.after_resist,
        after_armor=state.after_armor,
        after_magic_armor=state.magic_after_armor,
        after_absorb=state.total_damage,
        incoming_damage_cap=state.incoming_damage_cap or None,
    )

    res.is_hit = True
    tags = []
    if res.is_crit:
        tags.append("CRIT")
    res.events.append(
        CombatEventDTO(
            type="HIT",
            source_id=state.source_id,
            target_id=state.target_id,
            value=res.damage_final,
            resource="hp",
            tags=tags,
        )
    )
