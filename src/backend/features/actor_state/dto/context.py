from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ActorContextKind = Literal["player", "monster", "npc"]


class ActorContextMetaDTO(BaseModel):
    actor_type: ActorContextKind | str
    actor_id: int | str
    name: str
    role: str | None = None
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ActorContextSourceDTO(BaseModel):
    db_refs: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ActorRuntimeContextDTO(BaseModel):
    vitals: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class ActorCombatContextDTO(BaseModel):
    math_model: dict[str, Any] = Field(default_factory=dict)
    loadout: dict[str, Any] = Field(default_factory=dict)
    skills: dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class ActorInventoryContextDTO(BaseModel):
    equipped: list[dict[str, Any]] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    wallet: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class ActorStatusContextDTO(BaseModel):
    model_config = ConfigDict(extra="allow")


class ActorContextDTO(BaseModel):
    """Full contract for an on-demand temporary actor context.

    A context is a scoped projection built for a feature session. Missing
    optional sections stay null so callers can distinguish "not requested"
    from "requested and empty".
    """

    schema_version: int = 1
    meta: ActorContextMetaDTO
    source: ActorContextSourceDTO
    runtime: ActorRuntimeContextDTO | None = None
    combat: ActorCombatContextDTO | None = None
    inventory: ActorInventoryContextDTO | None = None
    status: ActorStatusContextDTO | None = None

    model_config = ConfigDict(extra="forbid")


__all__ = [
    "ActorCombatContextDTO",
    "ActorContextDTO",
    "ActorContextKind",
    "ActorContextMetaDTO",
    "ActorContextSourceDTO",
    "ActorInventoryContextDTO",
    "ActorRuntimeContextDTO",
    "ActorStatusContextDTO",
]
