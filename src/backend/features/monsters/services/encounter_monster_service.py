from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.monsters.dto.generation import (
    EncounterMonsterResult,
    GeneratedClan,
    GeneratedMonster,
    MonsterGenerationContext,
)
from src.backend.features.monsters.runtime.encounter_pool import EncounterPoolSelector
from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags

if TYPE_CHECKING:
    from src.backend.features.monsters.integrations import MonsterGenerationStorage
    from src.backend.features.monsters.runtime.clan_factory import ClanFactory


class EncounterMonsterService:
    def __init__(
        self,
        repository: MonsterGenerationStorage,
        factory: ClanFactory,
        pool: EncounterPoolSelector | None = None,
        assembler: MonsterGroupAssembler | None = None,
    ) -> None:
        self.repository = repository
        self.factory = factory
        self.pool = pool or EncounterPoolSelector()
        self.assembler = assembler or MonsterGroupAssembler()

    async def prepare_encounter_monsters(self, context: MonsterGenerationContext) -> EncounterMonsterResult:
        normalized_tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, normalized_tags)

        existing_clan = await self._choose_existing_clan(
            await self.repository.get_clans_by_context_hash(context_hash),
            context,
        )
        if existing_clan is not None:
            members = self._select_members(await self.repository.get_clan_members(existing_clan.id), context)
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
            clan = await self.factory.build_clan_template(
                context=context,
                family_id=family_id,
                context_hash=context_hash,
                unique_hash=unique_hash,
                normalized_tags=normalized_tags,
            )

        members = self._select_members(await self.repository.get_clan_members(clan.id), context)
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
            return clan

        return await self.factory.build_clan_template(
            context=context,
            family_id=family_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=normalized_tags,
        )

    async def _choose_existing_clan(
        self,
        clans: list[GeneratedClan],
        context: MonsterGenerationContext,
    ) -> GeneratedClan | None:
        if context.threat is None:
            return self.pool.choose_existing_clan(clans, context)
        for clan in sorted(clans, key=lambda existing: existing.unique_hash):
            if self._select_members(await self.repository.get_clan_members(clan.id), context):
                return clan
        return None

    def _select_members(
        self,
        members: list[GeneratedMonster],
        context: MonsterGenerationContext,
    ) -> list[GeneratedMonster]:
        if context.threat is None:
            return self.pool.select_monsters(members, context)
        assembly = self.assembler.assemble(
            members,
            budget=float(context.threat),
            tier=context.tier,
            danger=_context_danger(context),
        )
        return assembly.members


def _context_danger(context: MonsterGenerationContext) -> float:
    raw = context.context_meta.get("danger", 0.0)
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0
