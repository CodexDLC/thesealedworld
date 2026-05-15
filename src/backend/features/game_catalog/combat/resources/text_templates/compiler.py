from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from src.backend.features.game_catalog.combat.resources.text_templates.definitions import (
    ALL_COMBAT_TEXT_TEMPLATE_RECIPES,
)
from src.backend.features.game_catalog.combat.resources.text_templates.fragments import load_combat_text_phrases
from src.backend.features.game_catalog.combat.resources.text_templates.schemas import (
    CombatTextResourceIndexDTO,
    CombatTextTemplateDTO,
    CombatTextTemplateRecipeDTO,
)

COMBAT_TEXT_CATALOG_VERSION = "combat-text:2026-05-11.1"


def build_combat_text_catalog() -> dict[str, dict[str, Any]]:
    phrases = load_combat_text_phrases()
    templates: dict[str, dict[str, Any]] = {}
    resources: dict[str, dict[str, dict[str, Any]]] = {
        "feints": {},
        "basic_exchanges": {},
        "effects": {},
        "abilities": {},
        "deaths": {},
        "triggers": {},
        "gifts": {},
        "items": {},
    }
    grouped_template_keys: dict[tuple[str, str], list[str]] = defaultdict(list)

    for recipe in ALL_COMBAT_TEXT_TEMPLATE_RECIPES:
        compiled = compile_template_recipe(recipe, phrases)
        if compiled.key in templates:
            raise ValueError(f"Duplicate combat text template key: {compiled.key}")
        templates[compiled.key] = compiled.model_dump(mode="json")
        grouped_template_keys[(compiled.resource_type, compiled.resource_id)].append(compiled.key)

    for (resource_type, resource_id), template_keys in sorted(grouped_template_keys.items()):
        bucket = {
            "feint": "feints",
            "basic_exchange": "basic_exchanges",
            "effect": "effects",
            "ability": "abilities",
            "death": "deaths",
            "trigger": "triggers",
            "gift": "gifts",
            "item": "items",
        }[resource_type]
        first_template = templates[template_keys[0]]
        resources[bucket][resource_id] = CombatTextResourceIndexDTO(
            catalog_key=str(first_template["catalog_key"]),
            resource_type=resource_type,
            resource_id=resource_id,
            template_keys=sorted(template_keys),
        ).model_dump(mode="json")

    return {
        "meta": {"version": COMBAT_TEXT_CATALOG_VERSION},
        "templates": templates,
        "resources": resources,
    }


def compile_template_recipe(
    recipe: CombatTextTemplateRecipeDTO,
    phrases: dict[str, Any] | None = None,
) -> CombatTextTemplateDTO:
    phrase_registry = phrases or load_combat_text_phrases()
    resolved: dict[str, str] = {}
    variables: set[str] = set()
    for slot, phrase_key in recipe.phrase_keys.items():
        phrase = phrase_registry.get(phrase_key)
        if phrase is None:
            raise ValueError(f"Missing phrase key {phrase_key} for template {recipe.template_key}")
        resolved[slot] = phrase.text
        variables.update(phrase.variables)

    template = recipe.pattern.format_map(_TemplateSlotMap(resolved))

    unresolved_slots = set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", template))
    variables.update(unresolved_slots)

    return CombatTextTemplateDTO(
        key=recipe.template_key,
        template=template,
        variables=sorted(variables),
        resource_type=recipe.resource_type,
        resource_id=recipe.resource_id,
        catalog_key=recipe.catalog_key,
        outcome=recipe.outcome,
        body_pair=recipe.body_pair,
        target_body=recipe.target_body,
        delivery=recipe.delivery,
        phrase_keys=dict(recipe.phrase_keys),
        tags=list(recipe.tags),
    )


class _TemplateSlotMap(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
