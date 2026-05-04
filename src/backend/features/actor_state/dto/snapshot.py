from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from src.backend.infrastructure.actor_state.managers.snapshot import ActorSnapshotManager


def parse_csv_ids(value: Any, *, cast_int: bool = False) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            decoded = json.loads(stripped)
            raw_values = [item for item in decoded if item not in (None, "")]
        else:
            raw_values = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        raw_values = [item for item in value if item not in (None, "")]
    else:
        raw_values = [value]

    if cast_int:
        return [int(item) for item in raw_values]
    return [str(item) for item in raw_values]


def parse_csv_set(value: Any) -> set[str]:
    return {str(item).strip() for item in parse_csv_ids(value) if str(item).strip()}


class SnapshotsRequest(BaseModel):
    session_id: str
    player_ids: list[int] = Field(default_factory=list)
    monster_ids: list[str] = Field(default_factory=list)
    ttl: int = ActorSnapshotManager.DEFAULT_TTL_SECONDS
    include: set[str] | None = None
    exclude: set[str] = Field(default_factory=set)
    correlation_id: str | None = None
    request_id: str | None = None

    @field_validator("player_ids", mode="before")
    @classmethod
    def parse_player_ids(cls, value: Any) -> list[int]:
        return parse_csv_ids(value, cast_int=True)

    @field_validator("monster_ids", mode="before")
    @classmethod
    def parse_monster_ids(cls, value: Any) -> list[str]:
        return parse_csv_ids(value)

    @field_validator("ttl", mode="before")
    @classmethod
    def parse_ttl(cls, value: Any) -> int:
        if value in (None, ""):
            return ActorSnapshotManager.DEFAULT_TTL_SECONDS
        return int(value)

    @field_validator("include", mode="before")
    @classmethod
    def parse_include(cls, value: Any) -> set[str] | None:
        if value in (None, ""):
            return None
        return parse_csv_set(value)

    @field_validator("exclude", mode="before")
    @classmethod
    def parse_exclude(cls, value: Any, _info: ValidationInfo) -> set[str]:
        return parse_csv_set(value)


class ActorSnapshotBatchResult(BaseModel):
    snapshot_keys: dict[str, str] = Field(default_factory=dict)
    failed_players: list[int] = Field(default_factory=list)
    failed_monsters: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
