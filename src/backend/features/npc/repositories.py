from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.backend.features.npc.models import CharacterNpcEffectLog, CharacterNpcState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class NpcStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_state(self, *, character_id: int, npc_key: str, for_update: bool = False) -> CharacterNpcState | None:
        stmt = select(CharacterNpcState).where(
            CharacterNpcState.character_id == character_id,
            CharacterNpcState.npc_key == npc_key,
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_state(self, *, character_id: int, npc_key: str) -> CharacterNpcState:
        state = CharacterNpcState(character_id=character_id, npc_key=npc_key)
        self.session.add(state)
        await self.session.flush()
        return state

    async def get_or_create_state(
        self,
        *,
        character_id: int,
        npc_key: str,
        for_update: bool = False,
    ) -> CharacterNpcState:
        state = await self.get_state(character_id=character_id, npc_key=npc_key, for_update=for_update)
        if state is not None:
            return state
        state = await self.create_state(character_id=character_id, npc_key=npc_key)
        if for_update:
            state = await self.get_state(character_id=character_id, npc_key=npc_key, for_update=True) or state
        return state

    async def claim_effect_application(
        self,
        *,
        character_id: int,
        npc_key: str,
        idempotency_key: str,
        effect_count: int,
    ) -> bool:
        stmt = (
            insert(CharacterNpcEffectLog)
            .values(
                character_id=character_id,
                npc_key=npc_key,
                idempotency_key=idempotency_key,
                effect_count=effect_count,
            )
            .on_conflict_do_nothing(
                constraint="uq_character_npc_effect_logs_character_npc_idempotency",
            )
        )
        result = await self.session.execute(stmt)
        inserted = getattr(result, "rowcount", 0) or 0
        return inserted > 0

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
