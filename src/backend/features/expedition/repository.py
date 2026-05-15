from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from src.backend.features.expedition.models import CharacterExpedition

ACTIVE_EXPEDITION_STATUSES = ("active", "death_pending")


class CharacterExpeditionRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, run_id: str, *, for_update: bool = False) -> CharacterExpedition | None:
        stmt = select(CharacterExpedition).where(CharacterExpedition.run_id == run_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_character(
        self,
        char_id: int,
        *,
        for_update: bool = False,
    ) -> CharacterExpedition | None:
        stmt = (
            select(CharacterExpedition)
            .where(
                CharacterExpedition.character_id == char_id,
                CharacterExpedition.status.in_(ACTIVE_EXPEDITION_STATUSES),
            )
            .order_by(CharacterExpedition.started_at.desc())
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_active(
        self,
        *,
        char_id: int,
        start_location_id: str,
        current_location_id: str,
        respawn_anchor_location_id: str = "52_52",
    ) -> CharacterExpedition:
        expedition = CharacterExpedition(
            run_id=str(uuid.uuid4()),
            character_id=char_id,
            status="active",
            start_location_id=start_location_id,
            current_location_id=current_location_id,
            respawn_anchor_location_id=respawn_anchor_location_id or "52_52",
            pending_progress_json={},
            processed_events={},
        )
        self.session.add(expedition)
        await self.session.flush()
        return expedition

    def mark_processed(self, expedition: CharacterExpedition, event_key: str, payload: Any | None = None) -> bool:
        processed = dict(expedition.processed_events or {})
        if event_key in processed:
            return False
        processed[event_key] = {
            "processed_at": datetime.now(UTC).isoformat(),
            "payload": payload or {},
        }
        expedition.processed_events = processed
        return True

    @staticmethod
    def is_processed(expedition: CharacterExpedition, event_key: str) -> bool:
        return event_key in dict(expedition.processed_events or {})
