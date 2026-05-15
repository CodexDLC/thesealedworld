from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from src.backend.core.ai_json import parse_ai_json_model
from src.backend.features.items.prompts.router import build_item_name_description_prompt

if TYPE_CHECKING:
    from src.backend.core.ai import AIService

log = logging.getLogger(__name__)


class GeneratedItemTextDTO(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)


class ItemTextAIClient:
    """Items facade over AI text generation and prompt routing."""

    prompt_name = "item_name_description"

    def __init__(self, ai: AIService | None) -> None:
        self.ai = ai

    async def generate_item_text(self, payload: dict[str, Any]) -> GeneratedItemTextDTO | None:
        if self.ai is None:
            return None

        generated = await self.ai.generate_json(
            build_item_name_description_prompt(payload),
            schema=GeneratedItemTextDTO,
        )
        if generated is None:
            return None
        if isinstance(generated, GeneratedItemTextDTO):
            return generated
        return GeneratedItemTextDTO.model_validate(generated)

    def _parse_response(self, raw_text: Any) -> GeneratedItemTextDTO | None:
        parsed = parse_ai_json_model(raw_text, GeneratedItemTextDTO, context=self.prompt_name)
        if parsed is None:
            log.warning("Invalid AI item text response: %r", raw_text)
        return parsed
