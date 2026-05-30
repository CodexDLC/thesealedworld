from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
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

COMBAT_TEXT_CATALOG_VERSION = "combat-text:2026-05-17.4"


class CombatTextResolutionError(RuntimeError):
    pass


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


@lru_cache(maxsize=1)
def cached_combat_text_catalog() -> dict[str, dict[str, Any]]:
    return build_combat_text_catalog()


def get_combat_text_template(
    *,
    resource_type: str,
    resource_id: str,
    outcome: str,
    source_body: str = "",
    target_body: str = "",
    delivery: str = "default",
    tags: tuple[str, ...] = (),
) -> dict[str, Any]:
    body_pair = (
        f"{source_body}_to_{target_body}"
        if resource_type in {"basic_exchange", "feint"} and source_body and target_body
        else ""
    )
    templates = list(cached_combat_text_catalog()["templates"].values())
    for candidate_resource_id in _resource_id_candidates(resource_id):
        candidates = [
            template
            for template in templates
            if template.get("resource_type") == resource_type
            and template.get("resource_id") == candidate_resource_id
            and template.get("outcome") == outcome
        ]
        candidates = _select_combat_text_candidates(
            candidates,
            body_pair=body_pair,
            target_body=target_body,
            delivery=delivery,
            tags=tags,
        )
        if candidates:
            return dict(sorted(candidates, key=lambda template: str(template.get("key") or ""))[0])
    raise CombatTextResolutionError(
        "Missing combat_text template: "
        f"resource_type={resource_type} resource_id={resource_id} outcome={outcome} "
        f"body_pair={body_pair} target_body={target_body} delivery={delivery}"
    )


def _resource_id_candidates(resource_id: str) -> tuple[str, ...]:
    if resource_id == "default":
        return ("default",)
    return (resource_id, "default")


def _select_combat_text_candidates(
    candidates: list[dict[str, Any]],
    *,
    body_pair: str,
    target_body: str,
    delivery: str,
    tags: tuple[str, ...],
) -> list[dict[str, Any]]:
    candidates = _prefer_body_scope(candidates, body_pair=body_pair, target_body=target_body)
    candidates = _prefer_delivery(candidates, delivery=delivery)
    candidates = _prefer_tags(candidates, tags=tags)
    return candidates


def _prefer_body_scope(
    candidates: list[dict[str, Any]],
    *,
    body_pair: str,
    target_body: str,
) -> list[dict[str, Any]]:
    if not candidates:
        return []
    if body_pair:
        body_pair_candidates = [template for template in candidates if template.get("body_pair") == body_pair]
        if body_pair_candidates:
            return body_pair_candidates
    if target_body:
        target_candidates = [template for template in candidates if template.get("target_body") == target_body]
        if target_candidates:
            return target_candidates
    bodyless_candidates = [
        template for template in candidates if not template.get("body_pair") and not template.get("target_body")
    ]
    return bodyless_candidates


def _prefer_delivery(candidates: list[dict[str, Any]], *, delivery: str) -> list[dict[str, Any]]:
    if not candidates or not delivery:
        return candidates
    exact = [template for template in candidates if template.get("delivery") == delivery]
    if exact:
        return exact
    return [template for template in candidates if template.get("delivery") in {"", "default"}]


def _prefer_tags(candidates: list[dict[str, Any]], *, tags: tuple[str, ...]) -> list[dict[str, Any]]:
    if not candidates:
        return []
    for tag in tags:
        tagged = [template for template in candidates if tag in (template.get("tags") or [])]
        if tagged:
            return tagged
    return candidates


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
