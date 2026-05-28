from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.npc.repositories import NpcStateRepository
from src.backend.features.npc.services import DialogueNpcContext, NpcService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.npc.models import CharacterNpcState


class NpcIntegration:
    """Public NPC boundary for other backend features."""

    def __init__(self, service: NpcService) -> None:
        self.service = service

    @classmethod
    def from_session(cls, session: AsyncSession) -> NpcIntegration:
        return cls(NpcService(NpcStateRepository(session)))

    async def get_or_create_state(self, *, character_id: int, npc_key: str) -> CharacterNpcState:
        return await self.service.get_or_create_state(character_id=character_id, npc_key=npc_key)

    async def load_dialogue_context(self, *, character_id: int, npc_key: str) -> DialogueNpcContext:
        return await self.service.load_dialogue_context(character_id=character_id, npc_key=npc_key)

    async def apply_effects(
        self,
        *,
        character_id: int,
        npc_key: str,
        effects: list[dict[str, Any]],
        idempotency_key: str,
    ) -> dict[str, Any]:
        return await self.service.apply_effects(
            character_id=character_id,
            npc_key=npc_key,
            effects=effects,
            idempotency_key=idempotency_key,
        )


__all__ = ["NpcIntegration"]
