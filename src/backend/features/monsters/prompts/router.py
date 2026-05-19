from __future__ import annotations

import json
from typing import Any

from codex_ai.core import LLMRouter, PromptResult

monster_prompt_router = LLMRouter()


@monster_prompt_router.prompt("monster_clan_flavor")
async def build_monster_clan_flavor(payload: dict[str, Any], **kwargs: Any) -> PromptResult:
    return build_monster_clan_flavor_prompt(payload)


def build_monster_clan_flavor_prompt(payload: dict[str, Any]) -> PromptResult:
    system = """ROLE: Lead Narrative Designer for a dark fantasy RPG.
TASK: Create a unique Monster Clan identity from the provided creature family and location context.

Return JSON only:
{
  "name_ru": "Russian clan name",
  "description": "Russian atmospheric bestiary description, 3-4 sentences",
  "loot_culture": {
    "craft_style": "How this clan obtains, makes, steals, repairs, or repurposes equipment",
    "craft_skill_hint": "What their equipment workmanship looks like and what they can/cannot craft",
    "salvage_sources": ["3-8 concrete materials or objects they reuse for gear"],
    "tone_hints": ["3-8 item-description mood/style hints"],
    "equipment_origin_notes": ["2-6 concrete notes for item descriptions"]
  },
  "variants_flavor": [
    {
      "variant_key": "unit_key",
      "name": "Russian monster/variant title",
      "appearance": "Static visual bestiary description, 1-2 sentences",
      "detected": "Text when the player notices this monster first, 1 sentence",
      "ambush": "Text when this monster notices or attacks first, 1 sentence",
      "idle": "Text when this monster is seen before combat, standing or doing something, 1 sentence",
      "encounter": "Legacy fallback battle-start text; duplicate detected when unsure",
      "behavior": "Short behavioral note for fallback/internal use, 1 sentence"
    }
  ]
}

Rules:
- The clan name must include an organization word matching the group type: Банда, Стая, Рой, Клан, Орда, Легион, Гнездо.
- Do not use a plain species name as the whole name. Use a metaphor tied to environment and influence tags.
- Location context tags matter. Anchor/influence tags must visibly mutate appearance and behavior.
- If rift_profile is present, write the clan as a local rift-touched faction released or empowered by that rift.
- A rift is not a normal lair. Do not describe the creatures as living inside the rift; describe pressure, leakage, gathering, barricades, hunting grounds, or scavenging around it.
- Use rift_profile.boss_archetype and rift_profile.context_tags as a naming and atmosphere anchor.
- loot_culture is family-level equipment culture, not a specific dropped item. It must explain what this clan's gear is usually made from, how crude/skilled the workmanship is, and what environmental scraps shape their weapons, armor, shields, garments, or trophies.
- If loot_culture_seed is present, preserve its design direction but adapt it to the current location, biome, tags, tier, and rift_profile.
- For humanoid gangs in city ruins, prefer scavenged and stolen gear: gate plating, door boards, shop shutters, straps, nails, scrap metal, and repaired armor. For rift-touched clans, include rift-specific salvage from the payload.
- Tier 0-1 means ragged, hungry, weak, scavenging. Tier 5+ means ancient, evolved, or magically altered.
- Unit keys are technical ids from the input. Keep the same keys and write player-facing title/text fields for them.
- detected, ambush, and idle must describe different encounter states, not repeat appearance.
- Respect field length limits strictly:
  name_ru <= 80 chars;
  description <= 1200 chars;
  loot_culture.craft_style <= 300 chars and preferably 1 short sentence;
  loot_culture.craft_skill_hint <= 500 chars;
  variant.name <= 80 chars;
  variant.appearance <= 500 chars;
  variant.detected / ambush / idle / encounter <= 500 chars each;
  variant.behavior <= 300 chars.
- Russian only for player-facing strings.
- No markdown, no explanations."""
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return PromptResult(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,
        max_tokens=16000,
    )
