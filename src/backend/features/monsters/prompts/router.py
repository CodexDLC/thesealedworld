from __future__ import annotations

import json
from typing import Any

from codex_ai.core import LLMRouter, PromptResult

monster_prompt_router = LLMRouter()


@monster_prompt_router.prompt("monster_clan_flavor")
async def build_monster_clan_flavor(payload: dict[str, Any], **kwargs: Any) -> PromptResult:
    system = """ROLE: Lead Narrative Designer for a dark fantasy RPG.
TASK: Create a unique Monster Clan identity from the provided creature family and location context.

Return JSON only:
{
  "name_ru": "Russian clan name",
  "description": "Russian atmospheric bestiary description, 3-4 sentences",
  "variants_flavor": {
    "unit_key": {
      "name": "Russian monster/variant title",
      "appearance": "Static visual bestiary description, 1-2 sentences",
      "encounter": "Battle-start action text, 1-2 sentences",
      "behavior": "What it is doing or how it behaves, 1 sentence"
    }
  }
}

Rules:
- The clan name must include an organization word matching the group type: Банда, Стая, Рой, Клан, Орда, Легион, Гнездо.
- Do not use a plain species name as the whole name. Use a metaphor tied to environment and influence tags.
- Location context tags matter. Anchor/influence tags must visibly mutate appearance and behavior.
- Tier 0-1 means ragged, hungry, weak, scavenging. Tier 5+ means ancient, evolved, or magically altered.
- Unit keys are technical ids from the input. Keep the same keys and write player-facing title/text fields for them.
- Russian only for player-facing strings.
- No markdown, no explanations."""
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return PromptResult(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,
        max_tokens=2500,
    )
