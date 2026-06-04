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
  "display_name": {"ru": "Russian clan name", "en": "English clan name"},
  "description": {
    "ru": "Russian atmospheric bestiary description, 3-4 sentences",
    "en": "English atmospheric bestiary description, 3-4 sentences"
  },
  "visual_hint": {
    "ru": "Russian compact clan-level visual direction for image generation",
    "en": "English compact clan-level visual direction for image generation"
  },
  "encounter_texts": {
    "patrol": {"ru": "Russian patrol text, 1 sentence", "en": "English patrol text, 1 sentence"},
    "ambush": {"ru": "Russian ambush text, 1 sentence", "en": "English ambush text, 1 sentence"},
    "lair": {"ru": "Russian lair/node text, 1 sentence", "en": "English lair/node text, 1 sentence"},
    "random_meeting": {"ru": "Russian random meeting text, 1 sentence", "en": "English random meeting text, 1 sentence"}
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
      "display_name": {"ru": "Russian monster/variant title", "en": "English monster/variant title"},
      "short_description": {"ru": "Russian static member description, 1 sentence", "en": "English static member description, 1 sentence"},
      "appearance": {"ru": "Russian compact visible appearance, 1 sentence", "en": "English compact visible appearance, 1 sentence"},
      "visual_hint": {"ru": "Russian compact visual hint for image generation", "en": "English compact visual hint for image generation"}
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
- Do not put encounter, detected, ambush, idle, or behavior prose into variants_flavor. Variants only get title, short_description, appearance, and visual_hint.
- If selected_traits is present, use those traits to shape clan name, tone, encounter_texts, and member flavor.
- Every localized field must contain both ru and en. The English text must be a natural English rewrite, not transliterated Russian.
- Keep ru and en semantically equivalent enough for gameplay and search, but idiomatic in each language.
- Respect field length limits strictly:
  display_name.* <= 80 chars;
  description.* <= 1200 chars;
  visual_hint.* <= 300 chars;
  encounter_texts.*.* <= 500 chars each;
  loot_culture.craft_style <= 300 chars and preferably 1 short sentence;
  loot_culture.craft_skill_hint <= 500 chars;
  variant.display_name.* <= 80 chars;
  variant.short_description.* <= 300 chars;
  variant.appearance.* <= 300 chars;
  variant.visual_hint.* <= 300 chars.
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
