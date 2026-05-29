"""Final damage clamp: damage_mult, min-1 floor, incoming_damage_cap → res.damage_final."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    state.total_damage *= max(0.0, getattr(atk.mods, "damage_mult", 1.0))
    state.total_damage *= ctx.mods.damage_mult
    state.total_damage = max(0.0, state.total_damage)

    damage_channel_enabled = ctx.flags.damage.physical or ctx.flags.damage.pure or state.elemental_damage_enabled
    if damage_channel_enabled and state.raw_damage > 0.0:
        state.total_damage = max(1.0, state.total_damage)

    state.incoming_damage_cap = max(0, int(ctx.mods.incoming_damage_cap or 0))
    if state.incoming_damage_cap > 0 and state.total_damage > 0.0:
        state.total_damage = min(state.total_damage, float(state.incoming_damage_cap))

    res.damage_final = int(state.total_damage)

    if ctx.flags.damage.physical and state.base is not None:
        state.physical_added = max(0.0, float(state.base) - state.base_before_physical)
