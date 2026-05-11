from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING

from src.backend.features.monsters.dto.generation import (
    GeneratedClan,
    GeneratedMonster,
    MonsterGenerationContext,
    MonsterGroupMemberPreview,
    MonsterGroupResult,
)
from src.backend.features.monsters.resources import get_available_variants_for_tier, get_family_config
from src.backend.features.monsters.runtime.clan_factory import ClanFactory
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.combat_profile import build_monster_vitals
from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags

if TYPE_CHECKING:
    from src.backend.features.monsters.integrations import (
        MonsterActorCommitmentIntegration,
        MonsterGenerationStorage,
        MonsterGroupCacheIntegration,
        MonsterLocationContextIntegration,
    )


class MonsterGroupService:
    def __init__(
        self,
        *,
        repository: MonsterGenerationStorage,
        location_context: MonsterLocationContextIntegration,
        actor_commitments: MonsterActorCommitmentIntegration,
        group_cache: MonsterGroupCacheIntegration | None = None,
        factory: ClanFactory | None = None,
        assembler: MonsterGroupAssembler | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repository = repository
        self.location_context = location_context
        self.actor_commitments = actor_commitments
        self.group_cache = group_cache
        self.factory = factory or ClanFactory()
        self.assembler = assembler or MonsterGroupAssembler()
        self.actor_builder = MonsterCombatActorInputBuilder()
        self._rng = rng or random.Random()  # nosec B311

    async def prepare_monster_group(
        self,
        loc_id: str,
        budget: float,
        preferred_family_id: str | None = None,
        force_single_family: bool = True,
        *,
        scope_id: str | None = None,
        ttl: int = 300,
    ) -> MonsterGroupResult:
        location = await self.location_context.get_location_context(loc_id)
        context = MonsterGenerationContext(
            zone_id=location.zone_id,
            biome_id=location.biome_id,
            tier=location.tier,
            tags=location.tags,
            difficulty="mid",
        )
        normalized_tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, normalized_tags)
        clan, reused_existing_clan = await self._resolve_clan(
            context,
            context_hash,
            normalized_tags,
            preferred_family_id,
        )

        members = await self.repository.get_clan_members(clan.id)
        for member in members:
            if member.clan is None:
                member.clan = clan
        assembly = self.assembler.assemble(
            members,
            budget=budget,
            tier=location.tier,
            danger=location.danger,
            force_single_family=force_single_family,
        )
        if not assembly.members:
            raise ValueError(f"No generated monsters available for clan={clan.id}")

        group_id = str(scope_id or f"monster_group:{uuid.uuid4()}")
        sources = [self._materialize_actor_source(member) for member in assembly.members]
        actor_commitments = await self.actor_commitments.save_monster_sources(
            scope_id=group_id,
            sources=sources,
            ttl=ttl,
        )
        if len(actor_commitments) != len(sources):
            raise RuntimeError("Failed to save all monster actor commitments")

        previews = [self._preview(member) for member in assembly.members]
        result = MonsterGroupResult(
            group_id=group_id,
            clan_id=str(clan.id),
            family_id=clan.family_id,
            loc_id=location.loc_id,
            zone_id=location.zone_id,
            biome_id=location.biome_id,
            tier=location.tier,
            danger=location.danger,
            target_budget=assembly.target_budget,
            adjusted_budget=assembly.adjusted_budget,
            total_power=assembly.total_power,
            monster_ids=[str(member.id) for member in assembly.members],
            actor_commitments=actor_commitments,
            previews=previews,
            reused_existing_clan=reused_existing_clan,
            context_hash=context_hash,
            unique_hash=clan.unique_hash,
            tags=list(normalized_tags),
        )

        if self.group_cache is not None:
            group_key = await self.group_cache.save_group(
                group_id,
                self._group_payload(result),
                ttl=ttl,
            )
            result.group_key = group_key
        return result

    async def _resolve_clan(
        self,
        context: MonsterGenerationContext,
        context_hash: str,
        normalized_tags: list[str],
        preferred_family_id: str | None,
    ) -> tuple[GeneratedClan, bool]:
        if preferred_family_id:
            self._validate_preferred_family(context, preferred_family_id)

        existing = await self.repository.get_clans_by_context_hash(context_hash)
        existing = [clan for clan in existing if not preferred_family_id or clan.family_id == preferred_family_id]
        if existing:
            return self._choose_existing_clan(existing), True

        family_id = preferred_family_id or self.factory.select_family_id(context, context_hash)
        if family_id is None:
            raise ValueError(f"No monster families available for biome={context.biome_id} tier={context.tier}")

        unique_hash = compute_unique_clan_hash(family_id, context_hash)
        clan = await self.repository.get_clan_by_unique_hash(unique_hash)
        if clan is not None:
            return clan, True

        clan, members_to_create = await self.factory.build_clan_with_members(
            family_id=family_id,
            context=context,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=normalized_tags,
        )
        return await self.repository.create_clan_with_members(clan, members_to_create), False

    def _validate_preferred_family(self, context: MonsterGenerationContext, family_id: str) -> None:
        family = get_family_config(family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {family_id}")
        available = set(self.factory.get_available_family_ids(context))
        if family_id not in available or not get_available_variants_for_tier(family_id, context.tier):
            raise ValueError(
                f"Monster family is not available for biome={context.biome_id} tier={context.tier}: {family_id}"
            )

    def _choose_existing_clan(self, clans: list[GeneratedClan]) -> GeneratedClan:
        return self._rng.choice(sorted(clans, key=lambda clan: clan.unique_hash))

    def _materialize_actor_source(self, monster: GeneratedMonster) -> dict[str, object]:
        return self.actor_builder.build_snapshot(monster)

    def _preview(self, monster: GeneratedMonster) -> MonsterGroupMemberPreview:
        vitals = build_monster_vitals(monster)
        family_id = monster.family_id
        family = get_family_config(family_id) if family_id else None
        tags = ["monster", monster.role]
        if family is not None:
            tags.extend([family.id, family.archetype, *family.default_tags])
        return MonsterGroupMemberPreview(
            monster_id=str(monster.id),
            name=monster.name_ru,
            description=monster.description,
            role=monster.role,
            variant_key=monster.variant_key,
            threat_rating=monster.threat_rating,
            hp=dict(vitals.get("hp") or {}),
            tags=sorted(set(tags)),
        )

    @staticmethod
    def _group_payload(result: MonsterGroupResult) -> dict[str, object]:
        return result.model_dump(mode="json", exclude={"group_key"})
