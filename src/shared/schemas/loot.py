from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class LootTimestamps(BaseModel):
    created_at: float = Field(default_factory=time.time)
    public_at: float | None = None  # set on activate: created_at + 900
    decay_at: float | None = None  # set on activate: public_at + 3600


class LootItemDTO(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    template_id: str
    name: str
    icon: str | None = None
    rarity: str = "common"
    amount: int = 1
    layer: str = "drop"  # "drop" | "salvage" | "spoil"
    instance_id: str | None = None  # UUID of ItemInstance in PostgreSQL (None for resources)
    is_resource: bool = False  # True → ResourceWallet increment, not ItemPlacement
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorpseDTO(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    monster_name: str
    items: list[LootItemDTO] = Field(default_factory=list)
    is_visible: bool = False
    locked_to: list[int] = Field(default_factory=list)  # char_ids of winning team
    combat_id: str | None = None
    corpse_type: str = "monster"
    owner_char_id: int | None = None
    source_run_id: str | None = None
    access_policy: dict[str, Any] = Field(default_factory=dict)
    timestamps: LootTimestamps = Field(default_factory=LootTimestamps)

    @property
    def is_public(self) -> bool:
        if not self.is_visible:
            return False
        if self.timestamps.public_at is None:
            return False
        return time.time() > self.timestamps.public_at

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


class LootContainerDTO(BaseModel):
    corpses: list[CorpseDTO] = Field(default_factory=list)
    location_id: str | None = None


class ClaimResultDTO(BaseModel):
    instance_ids: list[str] = Field(default_factory=list)
    resource_deltas: dict[str, int] = Field(default_factory=dict)  # {template_id: amount}
