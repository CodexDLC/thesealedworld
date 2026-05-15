from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PhraseKind = Literal["approach", "contact", "impact", "reaction", "result", "natural_weapon", "weapon_form", "death"]


class CombatTextPhraseDTO(BaseModel):
    key: str
    kind: PhraseKind
    text: str
    variables: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_variables(self) -> CombatTextPhraseDTO:
        used = set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", self.text))
        declared = set(self.variables)
        missing = used - declared
        if missing:
            raise ValueError(f"Phrase {self.key} missing variables: {sorted(missing)}")
        return self


class CombatTextTemplateRecipeDTO(BaseModel):
    template_key: str
    resource_type: Literal["feint", "basic_exchange", "effect", "ability", "death", "trigger", "gift", "item"]
    resource_id: str
    catalog_key: str
    outcome: str
    body_pair: str = ""
    target_body: str = ""
    delivery: str = "default"
    pattern: str
    phrase_keys: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class CombatTextTemplateDTO(BaseModel):
    key: str
    template: str
    variables: list[str]
    resource_type: str
    resource_id: str
    catalog_key: str
    outcome: str
    body_pair: str
    target_body: str
    delivery: str
    phrase_keys: dict[str, str]
    tags: list[str] = Field(default_factory=list)


class CombatTextResourceIndexDTO(BaseModel):
    catalog_key: str
    resource_type: str
    resource_id: str
    template_keys: list[str] = Field(default_factory=list)
