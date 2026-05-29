"""Raw damage roll: base / spread / override_damage → raw_damage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.runtime.engine.math_core import MathCore

from ...support import offensive_lookup

UNARMED_MIN_EFFICIENCY = 0.5
UNARMED_MAX_EFFICIENCY = 3.0
UNARMED_NOVICE_SPREAD = 0.5
UNARMED_MASTER_SPREAD = 0.1

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
    state.source_id = res.source_id if res.source_id is not None else "0"
    state.target_id = res.target_id if res.target_id is not None else "0"

    if ctx.override_damage:
        state.min_d, state.max_d = ctx.override_damage
        state.base = None
        state.spread = None
    else:
        base = offensive_lookup.get_offensive_val(atk, ctx, "damage_base")
        spread = offensive_lookup.get_offensive_val(atk, ctx, "damage_spread")

        if ctx.flags.damage.physical:
            if ctx.flags.meta.weapon_class == "unarmed":
                unarmed = atk.skills.skill_unarmed
                efficiency = UNARMED_MIN_EFFICIENCY + ((UNARMED_MAX_EFFICIENCY - UNARMED_MIN_EFFICIENCY) * unarmed)
                base *= efficiency
                spread = max(UNARMED_MASTER_SPREAD, UNARMED_NOVICE_SPREAD - (0.4 * unarmed))
            base += atk.mods.physical_damage_bonus

        state.base = base
        state.spread = spread
        state.min_d = base * (1.0 - spread)
        state.max_d = base * (1.0 + spread)

    state.raw_damage = MathCore.random_range(state.min_d, state.max_d)
    state.base_before_physical = float(state.base or 0.0)

    state.armor_trace = {
        "raw": max(0.0, getattr(def_.mods, "armor", 0.0)),
        "effective": 0.0,
        "ignored": 0.0,
        "chance": 0.0,
        "roll": None,
        "passed": False,
    }
    state.phys_res_raw = max(0.0, getattr(def_.mods, "physical_resistance", 0.0))
    state.phys_suppression = max(0.0, offensive_lookup.get_offensive_val(atk, ctx, "physical_suppression"))
    state.phys_res_suppression_pct = (
        max(0.0, ctx.mods.physical_resistance_suppression_pct)
        if ctx.flags.formula.suppress_physical_resistance
        else 0.0
    )
    state.after_resist = state.raw_damage
    state.after_armor = state.raw_damage
