from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid


class MonsterGenerationContext(BaseModel):
    zone_id: str | None = None
    biome_id: str = "wasteland"
    tags: list[str] = Field(default_factory=list)
    tier: int = Field(ge=0, le=7)
    threat: int | None = Field(default=None, ge=0)
    difficulty: str = "mid"
    role: str | None = None
    count: int = Field(default=1, ge=1)


class EncounterMonsterResult(BaseModel):
    clan_id: str
    monster_ids: list[str]
    reused_existing_clan: bool
    context_hash: str
    unique_hash: str


@dataclass(slots=True)
class GeneratedClan:
    id: uuid.UUID
    family_id: str
    tier: int
    zone_id: str | None
    context_hash: str
    unique_hash: str
    raw_tags: dict[str, Any]
    flavor_content: dict[str, Any]
    name_ru: str
    description: str
    members: list[GeneratedMonster] = field(default_factory=list)


@dataclass(slots=True)
class GeneratedMonster:
    id: uuid.UUID
    clan_id: uuid.UUID
    variant_key: str
    role: str
    threat_rating: int
    name_ru: str
    description: str
    scaled_base_stats: dict[str, int]
    loadout_ids: dict[str, str] | list[str]
    skills_snapshot: list[str] | dict[str, Any]
    current_state: dict[str, Any] | None = None
    clan: GeneratedClan | None = None
