from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.monsters.dto.generation import EncounterMonsterResult, GeneratedClan, MonsterGenerationContext
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
            existing_clan = await self._refresh_clan_if_stale(existing_clan, context, normalized_tags)
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
            clan, members_to_create = await self.factory.build_clan_with_members(
                family_id=family_id,
                context=context,
                context_hash=context_hash,
                unique_hash=unique_hash,
                normalized_tags=normalized_tags,
            )
            clan = await self.repository.create_clan_with_members(clan, members_to_create)
        else:
            clan = await self._refresh_clan_if_stale(clan, context, normalized_tags)

        members = self.pool.select_monsters(await self.repository.get_clan_members(clan.id), context)
        return EncounterMonsterResult(
            clan_id=str(clan.id),
            monster_ids=[str(member.id) for member in members],
            reused_existing_clan=reused,
            context_hash=context_hash,
            unique_hash=unique_hash,
        )

    def get_available_family_ids(self, context: MonsterGenerationContext) -> list[str]:
        return self.factory.get_available_family_ids(context)

    async def ensure_clan_for_context(self, context: MonsterGenerationContext, family_id: str) -> GeneratedClan:
        available_family_ids = set(self.get_available_family_ids(context))
        if family_id not in available_family_ids:
            raise ValueError(
                f"Monster family is not available for biome={context.biome_id} tier={context.tier}: {family_id}"
            )

        normalized_tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, normalized_tags)
        unique_hash = compute_unique_clan_hash(family_id, context_hash)
        clan = await self.repository.get_clan_by_unique_hash(unique_hash)
        if clan is not None:
            return await self._refresh_clan_if_stale(clan, context, normalized_tags)

        clan, members_to_create = await self.factory.build_clan_with_members(
            family_id=family_id,
            context=context,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=normalized_tags,
        )
        return await self.repository.create_clan_with_members(clan, members_to_create)

    async def _refresh_clan_if_stale(
        self,
        clan: GeneratedClan,
        context: MonsterGenerationContext,
        normalized_tags: list[str],
    ) -> GeneratedClan:
        if not self.factory.should_refresh_clan_flavor(clan):
            return clan
        refreshed = await self.factory.refresh_clan_flavor(clan, context, normalized_tags)
        if refreshed is None:
            return clan
        return await self.repository.update_clan_flavor(refreshed)
