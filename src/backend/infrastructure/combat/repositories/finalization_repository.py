from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from src.backend.infrastructure.combat.models import CombatFinalization


class CombatFinalizationRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def upsert_from_payload(self, payload: dict[str, Any]) -> CombatFinalization:
        combat_id = str(payload["combat_id"])
        existing = await self.get_by_combat_id(combat_id)
        values = self._model_values(payload)
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

    async def get_latest_for_character(self, char_id: int) -> CombatFinalization | None:
        result = await self.session.execute(
            select(CombatFinalization)
            .where(CombatFinalization.participant_char_ids.contains([int(char_id)]))
            .order_by(CombatFinalization.finished_at.desc().nullslast(), CombatFinalization.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _model_values(payload: dict[str, Any]) -> dict[str, Any]:
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
        analytics = payload.get("analytics") if isinstance(payload.get("analytics"), dict) else {}
        reward_hooks = payload.get("reward_hooks") if isinstance(payload.get("reward_hooks"), list) else []
        return {
            "status": str(payload.get("status") or "finalized"),
            "source": _optional_str(meta.get("source")),
            "battle_type": _optional_str(meta.get("battle_type")),
            "location_id": _optional_str(meta.get("location_id")),
            "arena_session_id": _optional_str(meta.get("arena_session_id")),
            "winner_team": _optional_str(payload.get("winner_team")),
            "participant_char_ids": [int(value) for value in payload.get("participant_char_ids", [])],
            "started_at": _datetime_from_epoch(meta.get("started_at")),
            "finished_at": _datetime_from_epoch(payload.get("finished_at")),
            "finalization": payload,
            "analytics": analytics,
            "report": report,
            "reward_hooks": reward_hooks,
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
