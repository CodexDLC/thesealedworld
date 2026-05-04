from __future__ import annotations

from typing import Any
from codex_ai.core import LLMRouter, PromptResult

world_prompt_router = LLMRouter()

@world_prompt_router.prompt("zone_lore")
async def build_zone_lore(region_id: str, biome_id: str, tier: int, **kwargs: Any) -> PromptResult:
    """Builds a prompt to generate lore for a specific world zone."""
    system = (
        "You are a world-building assistant for a dark fantasy/post-apocalyptic MMORPG. "
        "The world is shattered, ancient technology is mixed with dark magic. "
        "Generate a name and a short background for a zone."
    )
    user = (
        f"Region: {region_id}\n"
        f"Biome: {biome_id}\n"
        f"Threat Tier: {tier}\n"
        "Generate a JSON response with 'name' (unique and atmospheric) and 'background' (1-2 sentences of history)."
    )
    return PromptResult(messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ])

@world_prompt_router.prompt("node_content")
async def build_node_content(
    x: int, 
    y: int, 
    terrain_type: str, 
    zone_name: str, 
    tags: list[str], 
    **kwargs: Any
) -> PromptResult:
    """Builds a prompt to generate descriptive content for a specific grid node."""
    system = (
        "You are an atmospheric writer for an RPG. "
        "Write short, evocative titles and descriptions for world locations."
    )
    tags_str = ", ".join(tags)
    user = (
        f"Location Coordinates: ({x}, {y})\n"
        f"Zone: {zone_name}\n"
        f"Terrain: {terrain_type}\n"
        f"Environmental Tags: {tags_str}\n\n"
        "Generate a JSON response with 'title' (atmospheric name) and 'description' (short evocative text)."
    )
    return PromptResult(messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ])
