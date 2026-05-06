from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.monsters.dto.generation import EncounterMonsterResult, MonsterGenerationContext
from src.backend.features.monsters.runtime.clan_factory import ClanFactory
from src.backend.features.monsters.runtime.encounter_pool import EncounterPoolSelector
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags

if TYPE_CHECKING:
    from src.backend.features.monsters.integrations import MonsterGenerationStorage


class EncounterMonsterService:
    def __init__(
        self,
        repository: MonsterGenerationStorage,
        factory: ClanFactory | None = None,
        pool: EncounterPoolSelector | None = None,
    ) -> None:
        self.repository = repository
        self.factory = factory or ClanFactory()
        self.pool = pool or EncounterPoolSelector()

    async def prepare_encounter_monsters(self, context: MonsterGenerationContext) -> EncounterMonsterResult:
        normalized_tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, normalized_tags)

        existing_clan = self.pool.choose_existing_clan(
            await self.repository.get_clans_by_context_hash(context_hash),
            context,
        )
        if existing_clan is not None:
            members = self.pool.select_monsters(await self.repository.get_clan_members(existing_clan.id), context)
            return EncounterMonsterResult(
                clan_id=str(existing_clan.id),
                monster_ids=[str(member.id) for member in members],
                reused_existing_clan=True,
                context_hash=context_hash,
                unique_hash=existing_clan.unique_hash,
            )

        family_id = self.factory.select_family_id(context, context_hash)
        if family_id is None:
            raise ValueError(f"No monster families available for biome={context.biome_id} tier={context.tier}")

        unique_hash = compute_unique_clan_hash(family_id, context_hash)
        clan = await self.repository.get_clan_by_unique_hash(unique_hash)
        reused = clan is not None
        if clan is None:
            clan, members_to_create = self.factory.build_clan_with_members(
                family_id=family_id,
                context=context,
                context_hash=context_hash,
                unique_hash=unique_hash,
                normalized_tags=normalized_tags,
            )
            clan = await self.repository.create_clan_with_members(clan, members_to_create)

        members = self.pool.select_monsters(await self.repository.get_clan_members(clan.id), context)
        return EncounterMonsterResult(
            clan_id=str(clan.id),
            monster_ids=[str(member.id) for member in members],
            reused_existing_clan=reused,
            context_hash=context_hash,
            unique_hash=unique_hash,
        )
