"""Pure damage channel: ignores resistances; crit gives flat 1.5x."""

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
    if not ctx.flags.damage.pure:
        return

    pure_dmg = state.raw_damage
    if res.is_crit:
        pure_dmg *= 1.5
    state.total_damage += pure_dmg
    state.damage_parts["pure"] = pure_dmg
