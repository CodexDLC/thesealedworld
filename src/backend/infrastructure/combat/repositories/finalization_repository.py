from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from src.backend.infrastructure.combat.models import CombatFinalization


class CombatFinalizationRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def upsert_from_payload(
        self,
        payload: dict[str, Any],
        *,
        mongo_document_id: str | None = None,
        mongo_status: str = "stored",
    ) -> CombatFinalization:
        combat_id = str(payload["combat_id"])
        existing = await self.get_by_combat_id(combat_id)
        values = self._model_values(payload, mongo_document_id=mongo_document_id, mongo_status=mongo_status)
        if existing is None:
            existing = CombatFinalization(combat_id=combat_id, **values)
            self.session.add(existing)
            await self.session.flush()
            return existing

        for key, value in values.items():
            setattr(existing, key, value)
        await self.session.flush()
        return existing

    async def get_by_combat_id(self, combat_id: str) -> CombatFinalization | None:
        result = await self.session.execute(
            select(CombatFinalization).where(CombatFinalization.combat_id == str(combat_id))
        )
        return result.scalar_one_or_none()

    async def get_all_for_backfill(self, *, limit: int = 500) -> list[CombatFinalization]:
        result = await self.session.execute(
            select(CombatFinalization)
            .order_by(CombatFinalization.finished_at.desc().nullslast(), CombatFinalization.id.desc())
            .limit(int(limit))
        )
        return list(result.scalars().all())

    async def get_latest_for_character(self, char_id: int) -> CombatFinalization | None:
        result = await self.session.execute(
            select(CombatFinalization)
            .where(CombatFinalization.participant_char_ids.contains([int(char_id)]))
            .order_by(CombatFinalization.finished_at.desc().nullslast(), CombatFinalization.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _model_values(
        payload: dict[str, Any],
        *,
        mongo_document_id: str | None = None,
        mongo_status: str = "stored",
    ) -> dict[str, Any]:
        raw_meta = payload.get("meta")
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
        return {
            "schema_version": int(payload.get("schema_version") or 2),
            "status": str(payload.get("status") or "finalized"),
            "source": _optional_str(meta.get("source")),
            "battle_type": _optional_str(meta.get("battle_type")),
            "location_id": _optional_str(meta.get("location_id")),
            "arena_session_id": _optional_str(meta.get("arena_session_id")),
            "winner_team": _optional_str(payload.get("winner_team")),
            "participant_char_ids": [int(value) for value in payload.get("participant_char_ids", [])],
            "player_win": _is_player_win(payload),
            "turns": _optional_int(report.get("turns") or report.get("last_turn")),  # type: ignore
            "started_at": _datetime_from_epoch(meta.get("started_at")),
            "finished_at": _datetime_from_epoch(payload.get("finished_at")),
            "mongo_document_id": _optional_str(mongo_document_id),
            "mongo_status": str(mongo_status or "stored"),
        }


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _datetime_from_epoch(value: Any) -> datetime | None:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    return datetime.fromtimestamp(numeric, tz=UTC)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_player_win(payload: dict[str, Any]) -> bool:
    winner_team = payload.get("winner_team")
    if not winner_team or winner_team == "draw":
        return False
    player_ids = {str(cid) for cid in payload.get("participant_char_ids", []) if cid is not None}
    if not player_ids:
        return False
    teams = payload.get("teams")
    if not isinstance(teams, dict):
        return False
    winner_members = teams.get(str(winner_team))
    if not isinstance(winner_members, list):
        return False
    return any(str(member) in player_ids for member in winner_members)
