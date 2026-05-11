from __future__ import annotations

from src.backend.features.game_catalog.combat.resources.basic_exchanges.definitions.weapon_attack_forms import (
    resolve_weapon_attack_form,
)
from src.backend.features.game_catalog.combat.resources.feints.schemas import FeintRenderContextDTO


def resolve_feint_render_context(
    *,
    feint_entry: object,
    skill_key: str | None,
    outcome: str,
    taxonomy: str = "humanoid",
    seed: str = "",
    bonus_damage: int | float = 0,
) -> FeintRenderContextDTO | None:
    descriptive = getattr(feint_entry, "descriptive", None)
    if descriptive is None:
        return None

    variant = descriptive.variants.get(taxonomy) or descriptive.variants.get(descriptive.default_taxonomy)
    if variant is None:
        return None

    use_templates = variant.event_texts.use
    outcome_templates = getattr(variant.event_texts, outcome, [])
    if not use_templates and not outcome_templates:
        return None

    if use_templates and outcome_templates:
        template = f"{use_templates[0]}, {outcome_templates[0]}"
    else:
        template = use_templates[0] if use_templates else outcome_templates[0]

    weapon_variables = resolve_weapon_attack_form(skill_key, seed=seed)
    weapon_variables["bonus_damage"] = _format_bonus_damage(bonus_damage)
    return FeintRenderContextDTO(
        template=template,
        event=outcome,
        taxonomy=taxonomy,
        variables=weapon_variables,
    )


def _format_bonus_damage(value: int | float) -> int | float:
    numeric = float(value or 0)
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 2)
