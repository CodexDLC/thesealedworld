from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArenaQueueRequestDTO(BaseModel):
    request_id: str = Field(default_factory=lambda: f"arena:request:{uuid.uuid4().hex}")
    char_id: int
    mode: str
    gs: int
    wait_limit_sec: int = 60
    commitment_id: str | None = None
    commitment_ttl: int | None = None
    start_time: float = Field(default_factory=time.time)


class ArenaCombatRequestDTO(BaseModel):
    source: Literal["arena"] = "arena"
    arena_session_id: str = Field(default_factory=lambda: f"arena:{uuid.uuid4().hex}")
    mode: str
    battle_type: Literal["pvp", "shadow"]
    requested_by: int
    participants: dict[str, list[int]]
    commitments: dict[str, str] = Field(default_factory=dict)
    status: Literal["pending", "ready", "failed"] = "pending"
    combat_id: str | None = None
    ttl: int | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)
