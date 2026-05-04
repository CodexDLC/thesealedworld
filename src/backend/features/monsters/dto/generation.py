from __future__ import annotations

from pydantic import BaseModel, Field


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

