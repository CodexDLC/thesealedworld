from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.shared.schemas.arena import ArenaScreenEnum


class ArenaRuntimeSessionDTO(BaseModel):
    arena_id: str = Field(default_factory=lambda: f"arena:runtime:{uuid.uuid4().hex}")
    char_id: int
    screen: ArenaScreenEnum = ArenaScreenEnum.MAIN_MENU
    mode: str | None = None
    mode_size: int = 1
    queue_request_id: str | None = None
    active_match_id: str | None = None
    combat_id: str | None = None
    season_id: int | None = None
    rating_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ArenaQueueRequestDTO(BaseModel):
    request_id: str = Field(default_factory=lambda: f"arena:request:{uuid.uuid4().hex}")
    char_id: int
    mode: str
    gs: int
    wait_limit_sec: int = 60
    commitment_id: str | None = None
    commitment_ttl: int | None = None
    start_time: float = Field(default_factory=time.time)
    mode_size: int = 1
    team_id: int | None = None
    season_id: int | None = None
    gs_locked: int | None = None
    gs_per_member: dict[str, int] = Field(default_factory=dict)
    member_ids: list[int] = Field(default_factory=list)


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
    mode_size: int = 1
    season_id: int | None = None
    entity_ids: dict[str, int] = Field(default_factory=dict)
    entity_types: dict[str, str] = Field(default_factory=dict)
    gs_locked: dict[str, int] = Field(default_factory=dict)
    gs_per_member: dict[str, dict[str, int]] = Field(default_factory=dict)
