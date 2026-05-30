from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select, update

from src.backend.infrastructure.combat.models import CombatAiSimulationRun


class CombatAiSimulationRunRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def create(
        self,
        *,
        run_kind: str,
        scenario_key: str,
        status: str,
        policy_ref: str | None,
        seed: int,
        max_rounds: int,
        rounds_completed: int,
        winner: str | None,
        reward: float | None,
        telemetry: dict[str, Any],
        report_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> CombatAiSimulationRun:
        row = CombatAiSimulationRun(
            id=str(uuid4()),
            run_kind=run_kind,
            scenario_key=scenario_key,
            status=status,
            policy_ref=policy_ref,
            seed=int(seed),
            max_rounds=int(max_rounds),
            rounds_completed=int(rounds_completed),
            winner=winner,
            reward=reward,
            telemetry=dict(telemetry),
            report_text=report_text,
            metadata_=dict(metadata or {}),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, run_id: str) -> CombatAiSimulationRun | None:
        return await self.session.scalar(select(CombatAiSimulationRun).where(CombatAiSimulationRun.id == str(run_id)))

    async def mark_completed(
        self,
        run_id: str,
        *,
        rounds_completed: int,
        reward: float | None,
        telemetry: dict[str, Any],
        report_text: str,
        metadata: dict[str, Any],
        winner: str | None = None,
    ) -> CombatAiSimulationRun | None:
        row = await self.get(run_id)
        if row is None:
            return None
        row.status = "completed"
        row.rounds_completed = int(rounds_completed)
        row.winner = winner
        row.reward = reward
        row.telemetry = dict(telemetry)
        row.report_text = report_text
        row.metadata_ = {**dict(metadata), "completed_at": datetime.now(UTC).isoformat()}
        await self.session.flush()
        return row

    async def update_running(
        self,
        run_id: str,
        *,
        rounds_completed: int,
        telemetry: dict[str, Any],
        report_text: str,
        metadata: dict[str, Any],
        winner: str | None = None,
        reward: float | None = None,
    ) -> CombatAiSimulationRun | None:
        row = await self.get(run_id)
        if row is None:
            return None
        row.status = "running"
        row.rounds_completed = int(rounds_completed)
        row.winner = winner
        row.reward = reward
        row.telemetry = dict(telemetry)
        row.report_text = report_text
        row.metadata_ = dict(metadata)
        await self.session.flush()
        return row

    async def mark_failed(self, run_id: str, *, error: dict[str, Any]) -> CombatAiSimulationRun | None:
        row = await self.get(run_id)
        if row is None:
            return None
        row.status = "failed"
        finished_at = datetime.now(UTC).isoformat()
        row.metadata_ = {
            **dict(row.metadata_ or {}),
            "error": error,
            "failed_at": finished_at,
            "completed_at": finished_at,
        }
        await self.session.flush()
        return row

    async def list_recent(self, *, limit: int = 50, run_kind: str | None = None) -> list[CombatAiSimulationRun]:
        stmt = select(CombatAiSimulationRun)
        if run_kind:
            stmt = stmt.where(CombatAiSimulationRun.run_kind == str(run_kind))
        stmt = stmt.order_by(CombatAiSimulationRun.created_at.desc()).limit(int(limit))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_completed_training_with_policy(self) -> CombatAiSimulationRun | None:
        stmt = (
            select(CombatAiSimulationRun)
            .where(CombatAiSimulationRun.run_kind == "training")
            .where(CombatAiSimulationRun.status == "completed")
            .order_by(CombatAiSimulationRun.created_at.desc())
            .limit(20)
        )
        result = await self.session.execute(stmt)
        for row in result.scalars().all():
            metadata = dict(row.metadata_ or {})
            if isinstance(metadata.get("best_policy"), dict):
                return row
        return None

    async def clear_all(self) -> int:
        result = await self.session.execute(delete(CombatAiSimulationRun))
        await self.session.flush()
        return int(result.rowcount or 0)

    async def clear_run_kinds(self, run_kinds: list[str]) -> int:
        if not run_kinds:
            return 0
        result = await self.session.execute(
            delete(CombatAiSimulationRun).where(CombatAiSimulationRun.run_kind.in_([str(kind) for kind in run_kinds]))
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def mark_running_stale(self, *, before: datetime) -> int:
        result = await self.session.execute(
            update(CombatAiSimulationRun)
            .where(CombatAiSimulationRun.status == "running")
            .where(CombatAiSimulationRun.created_at < before)
            .values(
                status="failed",
                metadata_=CombatAiSimulationRun.metadata_.op("||")(
                    {
                        "error": {
                            "type": "StaleSimulationRun",
                            "message": "Simulation run was still running after the stale cutoff.",
                        },
                        "failed_at": datetime.now(UTC).isoformat(),
                        "completion_reason": "stale_running_cleanup",
                    }
                ),
            )
        )
        await self.session.flush()
        return int(result.rowcount or 0)
