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
  "encounter_texts": {
    "patrol": "Clan-level text for a moving/travel patrol contact, 1 sentence",
    "ambush": "Clan-level text for a surprise or monster-initiated attack, 1 sentence",
    "lair": "Clan-level text for a guarded lair/node/boss position, 1 sentence",
    "random_meeting": "Clan-level text for an ordinary random meeting, 1 sentence"
  },
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
      "short_description": "Short static member description, 1 sentence",
      "visual_hint": "Optional compact visual hint for image generation"
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
- encounter_texts are clan-level prose, not individual monster prose. They must reflect the clan's traits, environment, organization, and rift context.
- If loot_culture_seed is present, preserve its design direction but adapt it to the current location, biome, tags, tier, and rift_profile.
- For humanoid gangs in city ruins, prefer scavenged and stolen gear: gate plating, door boards, shop shutters, straps, nails, scrap metal, and repaired armor. For rift-touched clans, include rift-specific salvage from the payload.
- Tier 0-1 means ragged, hungry, weak, scavenging. Tier 5+ means ancient, evolved, or magically altered.
- Unit keys are technical ids from the input. Keep the same keys and write player-facing title/text fields for them.
- Do not put encounter, detected, ambush, idle, or behavior prose into variants_flavor. Variants only get title, short_description, and optional visual_hint.
- If selected_traits is present, use those traits to shape clan name, tone, encounter_texts, and member flavor.
- Respect field length limits strictly:
  name_ru <= 80 chars;
  description <= 1200 chars;
  encounter_texts.* <= 500 chars each;
  loot_culture.craft_style <= 300 chars and preferably 1 short sentence;
  loot_culture.craft_skill_hint <= 500 chars;
  variant.name <= 80 chars;
  variant.short_description <= 300 chars;
  variant.visual_hint <= 300 chars.
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
