from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.frontend.core.api import BaseApiClient


@dataclass(frozen=True)
class CombatAiSimulationRun:
    id: str
    run_kind: str
    scenario_key: str
    status: str
    policy_ref: str
    seed: int
    max_rounds: int
    rounds_completed: int
    winner: str
    reward: float | None
    telemetry: dict[str, Any] = field(default_factory=dict)
    report_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CombatAiSimulationRun:
        return cls(
            id=str(data.get("id") or ""),
            run_kind=str(data.get("run_kind") or ""),
            scenario_key=str(data.get("scenario_key") or ""),
            status=str(data.get("status") or ""),
            policy_ref=str(data.get("policy_ref") or ""),
            seed=int(data.get("seed") or 0),
            max_rounds=int(data.get("max_rounds") or 0),
            rounds_completed=int(data.get("rounds_completed") or 0),
            winner=str(data.get("winner") or ""),
            reward=float(data["reward"]) if data.get("reward") is not None else None,
            telemetry=dict(data.get("telemetry") or {}),
            report_text=str(data.get("report_text") or ""),
            metadata=dict(data.get("metadata") or {}),
            created_at=str(data.get("created_at") or ""),
        )


class CombatAiTestingApi(BaseApiClient):
    async def list_runs(self, *, limit: int = 50, run_kind: str | None = None) -> list[CombatAiSimulationRun]:
        params: dict[str, Any] = {"limit": limit}
        if run_kind:
            params["run_kind"] = run_kind
        raw = await self._request("GET", "/api/admin/combat-ai/simulation-runs", params=params)
        return [CombatAiSimulationRun.from_dict(row) for row in (raw or {}).get("runs") or []]

    async def get_run(self, run_id: str) -> CombatAiSimulationRun | None:
        raw = await self._request("GET", f"/api/admin/combat-ai/simulation-runs/{run_id}")
        if not raw:
            return None
        return CombatAiSimulationRun.from_dict(raw)

    async def clear_runs(self) -> int:
        raw = await self._request("POST", "/api/admin/combat-ai/simulation-runs/clear")
        return int((raw or {}).get("deleted") or 0)

    async def clear_training_runs(self) -> int:
        raw = await self._request("POST", "/api/admin/combat-ai/simulation-runs/clear-training")
        return int((raw or {}).get("deleted") or 0)

    async def run_demo(
        self,
        *,
        seed: int = 0,
        max_rounds: int = 5,
        scenario_key: str = "starter_presets_5v5",
    ) -> CombatAiSimulationRun:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/demo",
            params={"seed": seed, "max_rounds": max_rounds, "scenario_key": scenario_key},
        )
        return CombatAiSimulationRun.from_dict(dict(raw or {}))

    async def run_family_pressure(
        self,
        *,
        family_id: str,
        imprint_key: str = "",
        seed: int = 0,
        trials: int = 10,
        max_rounds: int = 80,
        max_minions: int = 6,
        max_scenarios: int = 24,
    ) -> CombatAiSimulationRun:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/family-pressure",
            params={
                "family_id": family_id,
                "imprint_key": imprint_key,
                "seed": seed,
                "trials": trials,
                "max_rounds": max_rounds,
                "max_minions": max_minions,
                "max_scenarios": max_scenarios,
            },
            timeout=30.0,
        )
        return CombatAiSimulationRun.from_dict(dict(raw or {}))

    async def run_family_pressure_batch(
        self,
        *,
        family_id: str,
        seed: int = 0,
        trials: int = 10,
        max_rounds: int = 80,
        max_minions: int = 6,
        max_scenarios: int = 24,
    ) -> list[CombatAiSimulationRun]:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/family-pressure-batch",
            params={
                "family_id": family_id,
                "seed": seed,
                "trials": trials,
                "max_rounds": max_rounds,
                "max_minions": max_minions,
                "max_scenarios": max_scenarios,
            },
            timeout=30.0,
        )
        return [CombatAiSimulationRun.from_dict(row) for row in (raw or {}).get("runs") or []]

    async def train_synthetic(
        self,
        *,
        generations: int = 60,
        population: int = 32,
        seed: int = 0,
        sigma: float = 0.25,
    ) -> CombatAiSimulationRun:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/train-synthetic",
            params={"generations": generations, "population": population, "seed": seed, "sigma": sigma},
        )
        return CombatAiSimulationRun.from_dict(dict(raw or {}))

    async def train_battle(
        self,
        *,
        source_policy_run_id: str,
        generations: int = 12,
        population: int = 8,
        seed: int = 0,
        sigma: float = 0.15,
    ) -> CombatAiSimulationRun:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/train-battle",
            params={
                "source_policy_run_id": source_policy_run_id,
                "generations": generations,
                "population": population,
                "seed": seed,
                "sigma": sigma,
            },
        )
        return CombatAiSimulationRun.from_dict(dict(raw or {}))

    async def run_live_demo(
        self,
        *,
        seed: int = 0,
        max_rounds: int = 500,
        tick_interval_seconds: float = 0.05,
        timeout_ticks: int = 8,
        min_team_size: int = 5,
        max_team_size: int = 5,
        scenario_key: str = "starter_presets_5v5_live",
        policy_run_id: str = "",
    ) -> CombatAiSimulationRun:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/live-demo",
            params={
                "seed": seed,
                "max_rounds": max_rounds,
                "tick_interval_seconds": tick_interval_seconds,
                "timeout_ticks": timeout_ticks,
                "min_team_size": min_team_size,
                "max_team_size": max_team_size,
                "scenario_key": scenario_key,
                "policy_run_id": policy_run_id,
            },
        )
        return CombatAiSimulationRun.from_dict(dict(raw or {}))

    async def run_live_demo_batch(
        self,
        *,
        count: int,
        seed: int = 0,
        max_rounds: int = 500,
        tick_interval_seconds: float = 0.05,
        timeout_ticks: int = 8,
        min_team_size: int = 5,
        max_team_size: int = 5,
        scenario_key: str = "starter_presets_5v5_live",
        policy_run_id: str = "",
    ) -> list[CombatAiSimulationRun]:
        raw = await self._request(
            "POST",
            "/api/admin/combat-ai/simulation-runs/live-demo-batch",
            params={
                "count": count,
                "seed": seed,
                "max_rounds": max_rounds,
                "tick_interval_seconds": tick_interval_seconds,
                "timeout_ticks": timeout_ticks,
                "min_team_size": min_team_size,
                "max_team_size": max_team_size,
                "scenario_key": scenario_key,
                "policy_run_id": policy_run_id,
            },
            timeout=30.0,
        )
        return [CombatAiSimulationRun.from_dict(row) for row in (raw or {}).get("runs") or []]
