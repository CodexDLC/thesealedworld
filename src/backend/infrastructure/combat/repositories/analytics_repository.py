from __future__ import annotations

import json
from datetime import datetime  # noqa: TC003 - SQLAlchemy filters need this at runtime in method signatures.
from typing import Any

from sqlalchemy import bindparam, cast, delete, func, select
from sqlalchemy.dialects.postgresql import JSONPATH

from src.backend.infrastructure.combat.models import CombatBalanceRollup, CombatExchangeFact, CombatFinalization

FACT_DIMENSION_COLUMNS = {
    "weapon_base_id": CombatExchangeFact.weapon_base_id,
    "weapon_tier": CombatExchangeFact.weapon_tier,
    "armor_class": CombatExchangeFact.armor_class,
    "armor_tier": CombatExchangeFact.armor_tier,
    "feint_id": CombatExchangeFact.feint_id,
    "battle_type": CombatExchangeFact.battle_type,
    "location_id": CombatExchangeFact.location_id,
}


class CombatAnalyticsRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def replace_facts_for_combat(self, combat_id: str, facts: list[dict[str, Any]]) -> list[CombatExchangeFact]:
        await self.session.execute(delete(CombatExchangeFact).where(CombatExchangeFact.combat_id == str(combat_id)))
        rows = [
            CombatExchangeFact(**{**fact, "schema_version": int(fact.get("schema_version") or 2)}) for fact in facts
        ]
        if rows:
            self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def facts_for_buckets(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = select(CombatExchangeFact)
        if start is not None:
            stmt = stmt.where(CombatExchangeFact.finished_at >= start)
        if end is not None:
            stmt = stmt.where(CombatExchangeFact.finished_at < end)
        result = await self.session.execute(stmt)
        return [self._fact_to_dict(row) for row in result.scalars().all()]

    async def replace_rollups(
        self,
        rollups: list[dict[str, Any]],
        *,
        aggregate_version: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[CombatBalanceRollup]:
        stmt = delete(CombatBalanceRollup).where(CombatBalanceRollup.aggregate_version == int(aggregate_version))
        if start is not None:
            stmt = stmt.where(CombatBalanceRollup.bucket_start >= start)
        if end is not None:
            stmt = stmt.where(CombatBalanceRollup.bucket_start < end)
        await self.session.execute(stmt)
        rows = [
            CombatBalanceRollup(**{**rollup, "schema_version": int(rollup.get("schema_version") or 1)})
            for rollup in rollups
        ]
        if rows:
            self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def latest_aggregate_version(self) -> int | None:
        result = await self.session.execute(select(func.max(CombatBalanceRollup.aggregate_version)))
        value = result.scalar_one_or_none()
        return int(value) if value is not None else None

    async def rollup_filter_rows(
        self,
        *,
        aggregate_version: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(
                CombatBalanceRollup.dimensions,
                CombatBalanceRollup.metric_key,
                CombatBalanceRollup.bucket_grain,
                CombatBalanceRollup.bucket_start,
                CombatBalanceRollup.source_count,
            ).where(CombatBalanceRollup.aggregate_version == int(aggregate_version))
        )
        return [
            {
                "dimensions": row.dimensions or {},
                "metric_key": row.metric_key,
                "bucket_grain": row.bucket_grain,
                "bucket_start": row.bucket_start,
                "source_count": row.source_count or 0,
            }
            for row in result.all()
        ]

    async def query_rollups(
        self,
        *,
        aggregate_version: int,
        bucket_grain: str,
        start: datetime | None,
        end: datetime | None,
        metric_key: str | None,
        dimensions: dict[str, Any],
    ) -> list[dict[str, Any]]:
        stmt = select(CombatBalanceRollup).where(
            CombatBalanceRollup.aggregate_version == int(aggregate_version),
            CombatBalanceRollup.bucket_grain == bucket_grain,
        )
        if start is not None:
            stmt = stmt.where(CombatBalanceRollup.bucket_start >= start)
        if end is not None:
            stmt = stmt.where(CombatBalanceRollup.bucket_start < end)
        if metric_key:
            stmt = stmt.where(CombatBalanceRollup.metric_key == metric_key)
        if dimensions:
            stmt = stmt.where(CombatBalanceRollup.dimensions.contains(dimensions))
        stmt = stmt.order_by(
            CombatBalanceRollup.bucket_start, CombatBalanceRollup.metric_key, CombatBalanceRollup.dimensions_hash
        )
        result = await self.session.execute(stmt)
        return [self._rollup_to_dict(row) for row in result.scalars().all()]

    async def query_exchange_facts(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
        dimensions: dict[str, Any],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        stmt = select(CombatExchangeFact)
        if start is not None:
            stmt = stmt.where(CombatExchangeFact.finished_at >= start)
        if end is not None:
            stmt = stmt.where(CombatExchangeFact.finished_at < end)
        for key, value in dimensions.items():
            if key == "trigger_id":
                stmt = stmt.where(
                    func.jsonb_path_exists(
                        CombatExchangeFact.trigger_attempts,
                        cast(bindparam(f"trigger_path_{abs(hash(value))}", _trigger_id_jsonpath(value)), JSONPATH),
                    )
                )
                continue
            column = FACT_DIMENSION_COLUMNS.get(key)
            if column is not None:
                stmt = stmt.where(column == value)
        stmt = stmt.order_by(
            CombatExchangeFact.finished_at.desc().nullslast(),
            CombatExchangeFact.combat_id,
            CombatExchangeFact.turn,
            CombatExchangeFact.seq,
        )
        stmt = stmt.limit(int(limit)).offset(int(offset))
        result = await self.session.execute(stmt)
        return [self._fact_to_dict(row) for row in result.scalars().all()]

    async def get_finalization_analytics(self, combat_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            select(CombatFinalization.combat_id, CombatFinalization.analytics).where(
                CombatFinalization.combat_id == str(combat_id)
            )
        )
        row = result.first()
        if row is None:
            return None
        analytics = row.analytics if isinstance(row.analytics, dict) else {}
        return {"combat_id": row.combat_id, "analytics": analytics}

    async def query_combats_per_day(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = select(
            func.date(CombatFinalization.finished_at).label("date"),
            CombatFinalization.winner_team,
            CombatFinalization.battle_type,
            CombatFinalization.participant_char_ids,
            CombatFinalization.finalization["teams"].label("teams"),
        ).where(CombatFinalization.finished_at.is_not(None))
        if start is not None:
            stmt = stmt.where(CombatFinalization.finished_at >= start)
        if end is not None:
            stmt = stmt.where(CombatFinalization.finished_at < end)
        result = await self.session.execute(stmt)

        by_date: dict[str, dict[str, Any]] = {}
        for row in result.all():
            date_key = str(row.date)
            if date_key not in by_date:
                by_date[date_key] = {"date": date_key, "total": 0, "pve_total": 0, "pve_wins": 0, "pvp_total": 0}
            by_date[date_key]["total"] += 1
            is_pvp = (row.battle_type or "") in ("pvp", "shadow", "arena")
            if is_pvp:
                by_date[date_key]["pvp_total"] += 1
            else:
                by_date[date_key]["pve_total"] += 1
                if _is_player_win(row.winner_team, row.participant_char_ids, row.teams):
                    by_date[date_key]["pve_wins"] += 1
        return sorted(by_date.values(), key=lambda r: r["date"], reverse=True)

    async def query_win_stats(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[str, Any]]:
        stmt = select(
            CombatFinalization.battle_type,
            CombatFinalization.location_id,
            CombatFinalization.winner_team,
            func.count().label("cnt"),
        ).where(CombatFinalization.finished_at.is_not(None))
        if start is not None:
            stmt = stmt.where(CombatFinalization.finished_at >= start)
        if end is not None:
            stmt = stmt.where(CombatFinalization.finished_at < end)
        stmt = stmt.group_by(
            CombatFinalization.battle_type,
            CombatFinalization.location_id,
            CombatFinalization.winner_team,
        )
        result = await self.session.execute(stmt)
        return [
            {
                "battle_type": row.battle_type,
                "location_id": row.location_id,
                "winner_team": row.winner_team,
                "cnt": int(row.cnt),
            }
            for row in result.all()
        ]

    async def query_avg_rounds(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> dict[str, Any]:
        subq = select(
            CombatExchangeFact.combat_id,
            func.max(CombatExchangeFact.turn).label("max_turn"),
        )
        if start is not None:
            subq = subq.where(CombatExchangeFact.finished_at >= start)
        if end is not None:
            subq = subq.where(CombatExchangeFact.finished_at < end)
        subq = subq.group_by(CombatExchangeFact.combat_id).subquery()
        stmt = select(
            func.avg(subq.c.max_turn).label("avg"),
            func.min(subq.c.max_turn).label("min"),
            func.max(subq.c.max_turn).label("max"),
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None or row.avg is None:
            return {"avg": 0.0, "min": 0, "max": 0}
        return {"avg": round(float(row.avg), 2), "min": int(row.min or 0), "max": int(row.max or 0)}

    @staticmethod
    def _fact_to_dict(row: CombatExchangeFact) -> dict[str, Any]:
        return {
            column.name: getattr(row, column.name)
            for column in CombatExchangeFact.__table__.columns
            if column.name != "id"
        }

    @staticmethod
    def _rollup_to_dict(row: CombatBalanceRollup) -> dict[str, Any]:
        return {
            column.name: getattr(row, column.name)
            for column in CombatBalanceRollup.__table__.columns
            if column.name != "id"
        }


def _trigger_id_jsonpath(value: Any) -> str:
    return f"$[*] ? (@[0] == {json.dumps(str(value))})"


def _is_player_win(winner_team: Any, participant_char_ids: Any, teams: Any) -> bool:
    """True if the winning team contains at least one player character."""
    if not winner_team or winner_team == "draw":
        return False
    player_ids = {str(cid) for cid in (participant_char_ids or []) if cid is not None}
    if not player_ids:
        return False
    if not isinstance(teams, dict):
        return False
    team_members = teams.get(str(winner_team))
    if not isinstance(team_members, list):
        return False
    return any(str(m) in player_ids for m in team_members)
