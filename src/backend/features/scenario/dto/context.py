from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.backend.config.settings import settings

STAT_KEYS = [
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
]

ELEMENT_KEYS = ["fire", "water", "earth", "air", "dark", "arcane", "light", "nature"]


class ScenarioWeightsDTO(BaseModel):
    stats: dict[str, int] = Field(default_factory=lambda: {key: 0 for key in STAT_KEYS})
    elements: dict[str, int] = Field(default_factory=lambda: {key: 0 for key in ELEMENT_KEYS})


class ScenarioQueuesDTO(BaseModel):
    loot: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class ScenarioContextDTO(BaseModel):
    schema_version: int = 1
    scenario_session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    quest_key: str
    current_node_key: str
    step_counter: int = 0
    total_steps: int = 0
    visited_nodes: list[str] = Field(default_factory=list)
    weights: ScenarioWeightsDTO = Field(default_factory=ScenarioWeightsDTO)
    queues: ScenarioQueuesDTO = Field(default_factory=ScenarioQueuesDTO)
    sys_actor: str = settings.default_symbiote_name
    prev_state: str | None = None
    prev_loc: str | None = None
    flags: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(use_enum_values=True)

    def flatten(self) -> dict[str, Any]:
        flat: dict[str, Any] = {
            "schema_version": self.schema_version,
            "scenario_session_id": str(self.scenario_session_id),
            "quest_key": self.quest_key,
            "current_node_key": self.current_node_key,
            "step_counter": self.step_counter,
            "total_steps": self.total_steps,
            "visited_nodes": list(self.visited_nodes),
            "sys_actor": self.sys_actor,
            "prev_state": self.prev_state,
            "prev_loc": self.prev_loc,
            "p_loc": self.prev_loc,
            "loot_queue": list(self.queues.loot),
            "skills_queue": list(self.queues.skills),
            **self.flags,
        }
        flat.update({f"w_{key}": value for key, value in self.weights.stats.items()})
        flat.update({f"t_{key}": value for key, value in self.weights.elements.items()})
        return flat

    def apply_flat(self, flat: dict[str, Any]) -> None:
        for key, value in flat.items():
            if key.startswith("w_"):
                self.weights.stats[key[2:]] = int(value)
            elif key.startswith("t_"):
                self.weights.elements[key[2:]] = int(value)
            elif key == "loot_queue":
                self.queues.loot = list(value or [])
            elif key == "skills_queue":
                self.queues.skills = list(value or [])
            elif key in {"step_counter", "total_steps"}:
                setattr(self, key, int(value))
            elif key == "visited_nodes":
                self.visited_nodes = list(value or [])
            elif key in {"current_node_key", "sys_actor", "prev_state", "prev_loc"}:
                setattr(self, key, value)
            elif key not in {"scenario_session_id", "quest_key", "schema_version", "p_loc"}:
                self.flags[key] = value
        self.updated_at = datetime.now(UTC)
