"""Physical damage channel: crit multiplier + resistance + armor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...support import armor_math

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO

    from ._state import DamageState


def apply(
    state: DamageState,
    atk: ActorStats,
    def_: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
) -> None:
    if res.is_crit:
        state.crit_multiplier = armor_math.calculate_crit_multiplier(ctx)
        res.crit_mult = state.crit_multiplier

    if not ctx.flags.damage.physical:
        return

    phys_dmg = state.raw_damage

    if res.is_crit:
        phys_dmg *= state.crit_multiplier

    state.mitigation_pct = armor_math.effective_physical_resistance(atk, def_, ctx)
    phys_dmg *= 1.0 - state.mitigation_pct
    state.after_resist = phys_dmg

    state.armor_flat, state.armor_trace = armor_math.effective_armor_trace(
        atk,
        def_,
        ctx,
        incoming_damage=phys_dmg,
        res=res,
    )
    phys_dmg = max(0.0, phys_dmg - state.armor_flat)
    state.after_armor = phys_dmg
    state.damage_parts["physical"] = phys_dmg
    state.shield_guard_power = float(state.armor_trace.get("shield_guard_power") or 0.0)
    state.shield_mastery = max(0.0, min(1.0, float(def_.skills.skill_shield_mastery or 0.0)))
    state.shield_absorb_cap = state.after_resist if state.shield_guard_power > 0.0 else 0.0
    state.shield_absorb_ratio = float(state.armor_trace.get("pct") or 0.0) if state.shield_guard_power > 0.0 else 0.0
    total_power = float(state.armor_trace.get("total_power") or 0.0)
    shield_share = state.shield_guard_power / total_power if total_power > 0.0 else 0.0
    state.shield_absorb = state.armor_flat * shield_share

    state.total_damage += phys_dmg
