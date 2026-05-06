from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


class MonsterGenerationStorage(Protocol):
    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None: ...

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]: ...

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]: ...

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: list[GeneratedMonster],
    ) -> GeneratedClan: ...
