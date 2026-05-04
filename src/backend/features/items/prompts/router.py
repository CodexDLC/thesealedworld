from __future__ import annotations

import json
from typing import Any

from codex_ai.core import LLMRouter, PromptResult

item_prompt_router = LLMRouter()


@item_prompt_router.prompt("item_name_description")
async def build_item_name_description(payload: dict[str, Any], **kwargs: Any) -> PromptResult:
    system = (
        "You write item names and descriptions for a dark fantasy/post-apocalyptic MMORPG. "
        "The game server already computed all mechanics. Do not invent stats, damage, bonuses, prices, or rules. "
        "Use the provided item type, rarity, material, affixes, and narrative tags as inspiration only. "
        "Return strict JSON with keys 'name' and 'description'. Both values must be in Russian. "
        "The name must be short. The description must be 1-2 atmospheric sentences."
    )
    user = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return PromptResult(messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])

