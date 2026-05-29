"""Elemental damage loop (8 elements) + post-loop heavy-armor subsequent-hit penalty."""

from __future__ import annotations

from typing import TYPE_CHECKING

ELEMENTS = ("fire", "water", "air", "earth", "light", "darkness", "arcane", "nature")

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
    for elem in ELEMENTS:
        if getattr(ctx.flags.damage, elem, False):
            state.elemental_damage_enabled = True
            elem_dmg = state.raw_damage

            if res.is_crit:
                elem_dmg *= state.crit_multiplier

            resist_pct = getattr(def_.mods, f"{elem}_resistance", 0.0)
            pen_pct = 0.0

            if atk.mods.magical_penetration > 0:
                pen_pct = atk.mods.magical_penetration

            state.mitigation_pct = max(0.0, resist_pct - pen_pct)
            elem_dmg *= 1.0 - state.mitigation_pct
            state.total_damage += elem_dmg
            state.damage_parts[elem] = elem_dmg

    # Subsequent-hit heavy-armor penalty (applies to TOTAL after all channels accumulated).
    if ctx.flags.state.hit_index > 0:
        heavy_skill = def_.skills.skill_heavy_armor
        if heavy_skill > 0:
            state.total_damage *= 1.0 - (heavy_skill * 0.5)
