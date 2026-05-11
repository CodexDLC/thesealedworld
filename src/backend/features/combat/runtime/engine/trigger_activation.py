from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.combat.dto.pipeline import CombatTriggerActivationDTO, PipelineContextDTO

if TYPE_CHECKING:
    from src.backend.features.game_catalog.combat.resources.triggers.schemas import TriggerSource


def activate_trigger(
    ctx: PipelineContextDTO,
    trigger_id: str,
    *,
    source: TriggerSource = "system",
    source_id: str | None = None,
    source_slot: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    """Enable a trigger flag and record where it came from for this exchange."""
    field_name = _set_trigger_flag(ctx, trigger_id)
    if field_name is None:
        return False

    activations = ctx.trigger_activations.setdefault(field_name, [])
    candidate = CombatTriggerActivationDTO(
        trigger_id=field_name,
        source=source,
        source_id=source_id,
        source_slot=source_slot,
        tags=tags or [],
    )
    if not any(_same_activation(existing, candidate) for existing in activations):
        activations.append(candidate)
    return True


def _set_trigger_flag(ctx: PipelineContextDTO, trigger_id: str) -> str | None:
    if "." in trigger_id:
        parts = trigger_id.split(".")
        if len(parts) == 2:
            section_name, field_name = parts
            if hasattr(ctx.triggers, section_name):
                section = getattr(ctx.triggers, section_name)
                if hasattr(section, field_name):
                    setattr(section, field_name, True)
                    return field_name
        return None

    for _section_name, section_model in ctx.triggers:
        if hasattr(section_model, trigger_id):
            setattr(section_model, trigger_id, True)
            return trigger_id
    return None


def _same_activation(existing: CombatTriggerActivationDTO, candidate: CombatTriggerActivationDTO) -> bool:
    return (
        existing.trigger_id == candidate.trigger_id
        and existing.source == candidate.source
        and existing.source_id == candidate.source_id
        and existing.source_slot == candidate.source_slot
    )
