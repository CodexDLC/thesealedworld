from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.backend.features.monsters.resources import get_available_variants_for_tier, get_family_config
from src.backend.features.monsters.resources.spawn_config import BIOME_FAMILIES, TIER_AVAILABILITY, TIER_SCALING_CONFIG
from src.backend.infrastructure.actor_state.models import GeneratedClanORM, GeneratedMonsterORM

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.generation import MonsterGenerationContext
    from src.backend.features.monsters.dto.resources import MonsterFamilyDTO, MonsterVariantDTO


class ClanFactory:
    def select_family_id(self, context: MonsterGenerationContext, context_hash: str) -> str | None:
        candidates = sorted(self._select_candidates(context.tier, context.biome_id))
        if not candidates:
            return None
        index = int(context_hash[:8], 16) % len(candidates)
        return candidates[index]

    def build_clan_with_members(
        self,
        family_id: str,
        context: MonsterGenerationContext,
        context_hash: str,
        unique_hash: str,
        normalized_tags: Sequence[str],
    ) -> tuple[GeneratedClanORM, list[GeneratedMonsterORM]]:
        family = get_family_config(family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {family_id}")

        variant_ids = get_available_variants_for_tier(family_id, context.tier)
        if not variant_ids:
            raise ValueError(f"No monster variants for family={family_id} tier={context.tier}")

        flavor = self._build_flavor(family, context, variant_ids, normalized_tags)
        clan = GeneratedClanORM(
            id=uuid.uuid4(),
            family_id=family.id,
            tier=context.tier,
            zone_id=context.zone_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            raw_tags={"tags": list(normalized_tags), "biome_id": context.biome_id, "difficulty": context.difficulty},
            flavor_content=flavor,
            name_ru=str(flavor["name"]),
            description=str(flavor["description"]),
        )
        members = [self._build_member(clan.id, family, family.variants[variant_id], context.tier) for variant_id in variant_ids]
        return clan, members

    def _select_candidates(self, tier: int, biome_id: str) -> set[str]:
        in_biome = set(BIOME_FAMILIES.get(biome_id, set()))
        in_tier = set(TIER_AVAILABILITY.get(tier, set()))
        if "all_families" in in_tier:
            return in_biome
        candidates = in_biome & in_tier
        if candidates:
            return candidates
        return in_tier - {"all_families"}

    def _build_flavor(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        variant_ids: Sequence[str],
        normalized_tags: Sequence[str],
    ) -> dict[str, object]:
        tag_text = ", ".join(normalized_tags) if normalized_tags else "stable conditions"
        return {
            "name": f"{family.id.replace('_', ' ').title()} T{context.tier}",
            "description": f"{family.archetype.title()} {family.organization_type} adapted to {context.biome_id} under {tag_text}.",
            "variants": list(variant_ids),
        }

    def _build_member(
        self,
        clan_id: uuid.UUID,
        family: MonsterFamilyDTO,
        variant: MonsterVariantDTO,
        tier: int,
    ) -> GeneratedMonsterORM:
        multiplier = TIER_SCALING_CONFIG.get(tier, {"stat_mult": 1.0})["stat_mult"]
        base_stats = variant.base_stats.model_dump()
        return GeneratedMonsterORM(
            id=uuid.uuid4(),
            clan_id=clan_id,
            variant_key=variant.id,
            role=variant.role,
            threat_rating=variant.cost,
            name_ru=variant.id.replace("_", " ").title(),
            description=variant.narrative_hint,
            scaled_base_stats={key: int(value * multiplier) for key, value in base_stats.items()},
            loadout_ids=variant.fixed_loadout.model_dump(exclude_none=True),
            skills_snapshot=list(variant.skills),
            current_state=None,
        )
