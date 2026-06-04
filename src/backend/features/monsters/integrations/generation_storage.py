from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, HabitatClanPoolEntryDTO


class MonsterGenerationStorage(Protocol):
    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None: ...

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]: ...

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None: ...

    async def list_habitat_clan_pool_entries(
        self,
        *,
        scope_type: str,
        scope_id: str,
        enabled_only: bool = True,
    ) -> list[HabitatClanPoolEntryDTO]: ...

    async def upsert_habitat_clan_pool_entry(self, entry: HabitatClanPoolEntryDTO) -> HabitatClanPoolEntryDTO: ...

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]: ...

    async def delete_generated_clans_outside_zone_contexts(
        self,
        expected: dict[str, set[tuple[str, str]]],
    ) -> int: ...

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: list[GeneratedMonster],
    ) -> GeneratedClan: ...

    async def update_clan_narrative(self, clan: GeneratedClan) -> GeneratedClan: ...
