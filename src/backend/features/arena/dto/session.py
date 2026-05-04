from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArenaQueueRequestDTO(BaseModel):
    char_id: int
    mode: str
    gs: int
    start_time: float = Field(default_factory=time.time)


class ArenaCombatRequestDTO(BaseModel):
    source: Literal["arena"] = "arena"
    arena_session_id: str = Field(default_factory=lambda: f"arena:{uuid.uuid4().hex}")
    mode: str
    battle_type: Literal["pvp", "shadow"]
    requested_by: int
    participants: dict[str, list[int]]
    status: Literal["pending", "ready", "failed"] = "pending"
    combat_id: str | None = None
    ttl: int | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)
