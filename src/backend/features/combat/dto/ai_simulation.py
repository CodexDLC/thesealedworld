from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CombatAiSimulationRunDTO(BaseModel):
    id: str
    run_kind: str
    scenario_key: str
    status: str
    policy_ref: str | None = None
    seed: int
    max_rounds: int
    rounds_completed: int
    winner: str | None = None
    reward: float | None = None
    telemetry: dict[str, Any] = Field(default_factory=dict)
    report_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class CombatAiSimulationRunListDTO(BaseModel):
    runs: list[CombatAiSimulationRunDTO]
