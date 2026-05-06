from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, ValidationError

from src.backend.features.items.prompts.router import item_prompt_router

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
        if self.ai is not None:
            self.ai.include_router(item_prompt_router)

    async def generate_item_text(self, payload: dict[str, Any]) -> GeneratedItemTextDTO | None:
        if self.ai is None:
            return None

        raw_text = await self.ai.process(self.prompt_name, payload=payload)
        return self._parse_response(raw_text)

    def _parse_response(self, raw_text: Any) -> GeneratedItemTextDTO | None:
        if raw_text is None:
            return None
        raw_payload = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
        try:
            return GeneratedItemTextDTO.model_validate(raw_payload)
        except ValidationError:
            log.warning("Invalid AI item text response: %r", raw_text)
            return None
