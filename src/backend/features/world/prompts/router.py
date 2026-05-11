from __future__ import annotations

import json
from typing import Any

from codex_ai.core import LLMRouter, PromptResult

world_prompt_router = LLMRouter()


@world_prompt_router.prompt("zone_lore")
async def build_zone_lore(region_id: str, biome_id: str, tier: int, **kwargs: Any) -> PromptResult:
    """Builds a prompt to generate lore for a specific world zone."""
    narrative_context = kwargs.get("narrative_context")
    system = (
        "You are a world-building assistant for a dark fantasy/post-apocalyptic MMORPG. "
        "The world is shaped by four Anchor Monoliths: north is stasis/ice, south is plasma/fire, "
        "west is gravity/storm, east is biomass/mutation. These are anomalous pressures, not normal weather. "
        "Generate a name and a short background for a zone."
    )
    user = (
        f"Region: {region_id}\n"
        f"Biome: {biome_id}\n"
        f"Threat Tier: {tier}\n"
        f"Narrative Context: {narrative_context or 'No extra narrative context.'}\n"
        "Generate a JSON response with 'name' (unique and atmospheric) and 'background' (1-2 sentences of history)."
    )
    return PromptResult(messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])


@world_prompt_router.prompt("node_content")
async def build_node_content(
    x: int, y: int, terrain_type: str, zone_name: str, tags: list[str], **kwargs: Any
) -> PromptResult:
    """Builds a prompt to generate descriptive content for a specific grid node."""
    system = (
        "You are an atmospheric writer for an RPG. Write short, evocative titles and descriptions for world locations. "
        "Ancient technology looks like magic: seamless stone, obsidian, white monolith, glowing runes, crystalline channels. "
        "Elemental tags are anomalous energy leaking from Anchor Monoliths, not ordinary weather. "
        "Inside safe zones describe anchor influence as subtle pressure or sensation, not as disaster."
    )
    tags_str = ", ".join(tags)
    user = (
        f"Location Coordinates: ({x}, {y})\n"
        f"Zone: {zone_name}\n"
        f"Terrain: {terrain_type}\n"
        f"Environmental Tags: {tags_str}\n\n"
        "Generate a JSON response with 'title' (atmospheric name) and 'description' (short evocative text)."
    )
    return PromptResult(messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])


@world_prompt_router.prompt("batch_location_desc")
async def build_batch_location_desc(payload_items: list[dict[str, Any]], **kwargs: Any) -> PromptResult:
    """Build the legacy batch prompt for location names/descriptions from tags."""
    system = """ROLE: Narrative Designer for 'Echo of Ancients' (Post-Apocalyptic Techno-Fantasy RPG).
SETTING: A world of ancient, high-tech ruins ("The Ancients") reclaimed by nature and scavengers.

STYLE GUIDE (STRICTLY ADHERE):
1. **The Ancients (Environment/Ruins):**
   - Materials: Seamless stone, obsidian, white marble, gold veins, crystals.
   - Technology: Looks like magic. Levitating rocks, glowing runes, humming monoliths.
   - FORBIDDEN for Ancients: Rust, wires, bolts, rivets, concrete, asphalt, plastic, steam pipes. Use "crystalline circuits" or "ether channels" instead.
2. **The Survivors (Current Inhabitants):**
   - Materials: Rotting wood, scraps of rusty metal (brought from outside), coarse cloth, bone, fire.
   - Contrast: Describe primitive tents/barricades leaning against indestructible, glowing ancient walls.
3. **The Rift Energy (CRITICAL):**
   - Elemental tags (ice, fire, gravity, bio) are NOT weather. They are **anomalous energy leaking from the Anchors**.
   - "Ice" is Stasis/Entropy, not just winter. It feels like time stopping.
   - "Fire" is Atomic decay/Plasma, not just a campfire heat.
   - "Bio" is forced mutation/evolution, not just plants.
   - **Inside Safe Zones (Tier 0 tags like 'morning_chill', 'static_tingle'):** Describe this as a subtle, supernatural sensation ("breath of the monolith", "tingling of the skin"), NOT as physical weather.
4. **Atmosphere:** Majestic, melancholic, dangerous. A contrast between Eternal Perfection (ruins) and Temporary Decay (survivors/nature).

INPUT FORMAT:
A JSON list of objects:
[{"id": "52_52", "tags": ["ancient_city", "hub_center", "tents"], "context": ["На севере виднеется Шпиль"], "route_context": null, "boundary_context": {}}]
- route_context is optional route metadata. If present with must_describe=true, the route/road/path is a physical navigation element in the scene and must be described.
- boundary_context is optional directional walls, gates, blocked edges, or sealed borders. If present, describe the boundary on the correct side without turning it into a separate room.

BATCH SEMANTICS:
- A full batch may contain 25 locations. Treat it as one coherent 5x5 sector inside a region.
- Each location ID is a sublocation inside that sector: a street segment, courtyard, hall, plaza edge, block entrance, collapsed house row, gate approach, or another navigable sub-area.
- Keep continuity across the batch. Neighboring sublocations should feel like parts of the same district, not unrelated random rooms.
- Do not make every sublocation equally epic. Give the sector a shared identity, then vary details, scale, sightlines, damage, barricades, stonework, roads, walls, and anomaly traces.
- Road tags are literal. If tags include road, track, path, highway, bridge, ancient_highway, or broken_road, the description must include the visible route and how it shapes movement through the sublocation.
- Boundary tags are literal. If boundary_context contains a wall or gate, describe it as an edge/side feature of the current sublocation, not as a separate impassable room.

OUTPUT FORMAT:
A single JSON object. Keys are location IDs.
{
  "52_52": {
    "title": "Площадь Резонанса",
    "description": "Величественная площадь из белого монолита, который не берет время. Посреди идеальных плит вырос хаотичный палаточный лагерь выживших. На севере, пронзая небо, виднеется Шпиль Хаба."
  }
}

RULES:
1. **Language**: RUSSIAN.
2. **Title**: Evocative, 2-5 words.
3. **Description**: 3-5 sentences (90-140 words).
   - Sentence 1: Visuals/Atmosphere (Ancient tech + Nature/Decay).
   - Sentence 2: Details from "tags".
   - Sentence 3+: Integrate "context" landmarks naturally and show how this sublocation fits the surrounding sector.
4. **Context is MANDATORY**: You MUST mention landmarks from "context" input.
5. **Tag Logic**:
   - "_center": High intensity (e.g., "heart of the anomaly").
   - "_edge": Transition zone.
   - "frozen/ice": Not just snow, but "stasis", "crystalline growth", "stopped time".
   - "magma/fire": "Entropy", "disintegration", "liquid rock".
   - "gravity": "Floating debris", "upward rain", "distorted horizon".
   - "bio": "Mutated flora", "flesh-like moss", "giant roots crushing stone".
6. **Completeness is mandatory**: Return one entry for every input id. Do not omit ids. Do not add extra ids.
7. **NO REPETITION**: Use varied vocabulary. Avoid starting every description with "Здесь...".
8. **No mechanics invention**: Do not invent loot, enemies, NPCs, quests, interactable services, unlocked paths, or rewards unless directly implied by tags.
9. **Return ONLY the complete JSON object.**
"""
    user = json.dumps(payload_items, ensure_ascii=False, sort_keys=True)
    return PromptResult(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.7,
        max_tokens=16000,
    )
