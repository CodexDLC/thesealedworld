from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from src.backend.features.exploration.models import CharacterLocationKnowledge

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CharacterLocationKnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, char_id: int, loc_id: str) -> CharacterLocationKnowledge | None:
        stmt = select(CharacterLocationKnowledge).where(
            CharacterLocationKnowledge.character_id == char_id,
            CharacterLocationKnowledge.loc_id == loc_id,
        )
        return await self.session.scalar(stmt)

    async def upsert_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        table = cast("Any", CharacterLocationKnowledge.__table__)
        stmt = insert(table).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                table.c.character_id,
                table.c.loc_id,
            ],
            set_={
                "movement_xp_spent": stmt.excluded.movement_xp_spent,
                "scouting_xp_spent": stmt.excluded.scouting_xp_spent,
                "hunting_xp_spent": stmt.excluded.hunting_xp_spent,
                "movement_xp_cap": stmt.excluded.movement_xp_cap,
                "scouting_xp_cap": stmt.excluded.scouting_xp_cap,
                "hunting_xp_cap": stmt.excluded.hunting_xp_cap,
                "discovered_at": stmt.excluded.discovered_at,
                "last_visited_at": stmt.excluded.last_visited_at,
                "metadata": stmt.excluded["metadata"],
                "context": stmt.excluded.context,
                "source_context": stmt.excluded.source_context,
                "schema_version": stmt.excluded.schema_version,
                "revision": table.c.revision + 1,
                "updated_at": func.now(),
            },
        )
        await self.session.execute(stmt)
