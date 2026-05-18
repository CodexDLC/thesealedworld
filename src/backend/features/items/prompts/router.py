from __future__ import annotations

import json
from typing import Any

from codex_ai.core import LLMRouter, PromptResult

item_prompt_router = LLMRouter()


@item_prompt_router.prompt("item_name_description")
async def build_item_name_description(payload: dict[str, Any], **kwargs: Any) -> PromptResult:
    return build_item_name_description_prompt(payload)


def build_item_name_description_prompt(payload: dict[str, Any]) -> PromptResult:
    system = (
        'You write item names and descriptions for a dark fantasy / post-apocalyptic MMORPG ("Echo of Ancients"). '
        "The world is shaped by four Anchor Monoliths: north=stasis/ice, south=plasma/fire, west=gravity/storm, east=biomass/mutation. "
        "Ancient technology looks like magic. Elemental tags are anomalous energy from Anchors, not ordinary weather. "
        "The game server computed all mechanics. Do not invent stats, damage, bonuses, prices, or rules. "
        "\n\n"
        "SOURCE CONTEXT RULES (critical): "
        "If source_context is present and contains monster or clan data (monster_family_id, monster_family_tags, "
        "clan_archetype, clan_organization, owner_family), use it to give the item a racial or faction identity in the description "
        "— a hint of who owned, made, or carried this item. A blade from a bandit gang should feel outlaw-worn; "
        "a hide piece from a mutant swarm should feel feral or corrupted; a garment from nomadic humans should feel worn-travel. "
        "Do not name the faction explicitly — suggest it through material wear, cultural details, or purpose. "
        "If owner_family.loot_culture is present, treat it as the strongest equipment-culture source: craft_style, craft_skill_hint, "
        "salvage_sources, tone_hints, and equipment_origin_notes should shape the name and description. "
        "Do not write a specific monster individual's name unless it is explicitly present in the item base identity. "
        "If source_context contains location data (location_tags, biome_id, anchor_influence_tags), let the environment "
        "flavor bleed into the description where it fits naturally. "
        "If source_context is missing or sparse, write purely from type, material, grade, and stable item tags. "
        "\n\n"
        "Use provided tags, type, material, grade, and source context as narrative inspiration only. "
        "Write in Russian. Name: short (2-5 words). Description: 1-2 atmospheric sentences (25-60 words). "
        'Return strict JSON: {"name": "...", "description": "..."}.'
    )
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return PromptResult(messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
