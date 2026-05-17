from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratedItemTextDTO(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
