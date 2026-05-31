from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


class MonsterGenerationStorage(Protocol):
    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None: ...

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]: ...

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None: ...

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]: ...

    async def delete_generated_clans_outside_zone_contexts(
        self,
        expected: dict[str, set[tuple[str, str]]],
    ) -> int: ...

    async def refresh_clan_gear_scores(
        self,
        clan_id: uuid.UUID | str,
        *,
        gear_score_service,
        persist: bool = False,
    ) -> list[GeneratedMonster]: ...

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: list[GeneratedMonster],
    ) -> GeneratedClan: ...

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan: ...
