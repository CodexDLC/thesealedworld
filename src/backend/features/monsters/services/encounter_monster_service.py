from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.monsters.runtime.hashing import (
    MonsterHashContext,
    compute_context_hash,
    compute_monster_context_hash,
    compute_unique_clan_hash,
    normalize_tags,
    normalized_monster_hash_tags,
)

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, MonsterGenerationContext
    from src.backend.features.monsters.integrations import MonsterGenerationStorage
    from src.backend.features.monsters.runtime.clan_factory import ClanFactory


class EncounterMonsterService:
    def __init__(
        self,
        repository: MonsterGenerationStorage,
        factory: ClanFactory,
    ) -> None:
        self.repository = repository
        self.factory = factory

    def get_available_family_ids(self, context: MonsterGenerationContext) -> list[str]:
        return self.factory.get_available_family_ids(context)

    async def prune_generated_clans_for_zone_contexts(self, expected: dict[str, set[tuple[str, str]]]) -> int:
        delete_generated_clans = getattr(self.repository, "delete_generated_clans_outside_zone_contexts", None)
        if not callable(delete_generated_clans):
            return 0
        return int(await delete_generated_clans(expected))

    async def ensure_clan_for_context(self, context: MonsterGenerationContext, family_id: str) -> GeneratedClan:
        normalized_tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, normalized_tags)
        return await self._ensure_clan(
            context,
            family_id,
            context_hash=context_hash,
            normalized_tags=normalized_tags,
        )

    async def ensure_clan_for_hash_context(
        self,
        context: MonsterGenerationContext,
        family_id: str,
        *,
        hash_context: MonsterHashContext,
    ) -> GeneratedClan:
        return await self._ensure_clan(
            context,
            family_id,
            context_hash=compute_monster_context_hash(hash_context),
            normalized_tags=normalized_monster_hash_tags(hash_context),
        )

    async def _ensure_clan(
        self,
        context: MonsterGenerationContext,
        family_id: str,
        *,
        context_hash: str,
        normalized_tags: list[str],
    ) -> GeneratedClan:
        available_family_ids = set(self.get_available_family_ids(context))
        if family_id not in available_family_ids:
            raise ValueError(
                f"Monster family is not available for biome={context.biome_id} tier={context.tier}: {family_id}"
            )

        unique_hash = compute_unique_clan_hash(family_id, context_hash)
        clan = await self.repository.get_clan_by_unique_hash(unique_hash)
        if clan is not None:
            return clan

        return await self.factory.build_clan_template(
            context=context,
            family_id=family_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=normalized_tags,
        )
