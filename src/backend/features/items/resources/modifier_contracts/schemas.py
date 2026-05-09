from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ModifierOperation = Literal["add", "mult", "set"]
ModifierLayer = Literal["attributes", "modifiers", "world", "auto"]


@dataclass(frozen=True)
class ModifierContractDTO:
    id: str
    target_field: str
    operation: ModifierOperation
    value_kind: str
    default_layer: ModifierLayer = "auto"
    formatter_hint: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
