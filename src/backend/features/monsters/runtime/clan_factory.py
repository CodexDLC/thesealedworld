from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.resources import (
    get_available_variants_for_tier,
    get_available_variants_for_tier_window,
    get_family_config,
)
from src.backend.features.monsters.resources.spawn_config import BIOME_FAMILIES, TIER_AVAILABILITY, TIER_SCALING_CONFIG
from src.backend.features.monsters.runtime.combat_profile import build_monster_combat_seed

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.generation import MonsterGenerationContext
    from src.backend.features.monsters.dto.resources import MonsterFamilyDTO, MonsterVariantDTO
    from src.backend.features.monsters.integrations import MonsterClanTextAIClient


class ClanFactory:
    def __init__(self, text_ai: MonsterClanTextAIClient | None = None) -> None:
        self.text_ai = text_ai

    def get_available_family_ids(self, context: MonsterGenerationContext) -> list[str]:
        candidates = sorted(self._select_candidates(context.tier, context.biome_id))
        return [
            family_id
            for family_id in candidates
            if get_family_config(family_id) is not None and get_available_variants_for_tier(family_id, context.tier)
        ]

    def select_family_id(self, context: MonsterGenerationContext, context_hash: str) -> str | None:
        candidates = self.get_available_family_ids(context)
        if not candidates:
            return None
        index = int(context_hash[:8], 16) % len(candidates)
        return candidates[index]

    def should_refresh_clan_flavor(self, clan: GeneratedClan) -> bool:
        if not isinstance(clan.flavor_content.get("variants_flavor"), dict):
            return True
        if _looks_generated_placeholder(clan.name_ru):
            return True
        return any(_looks_generated_placeholder(member.name_ru) for member in clan.members)

    async def refresh_clan_flavor(
        self,
        clan: GeneratedClan,
        context: MonsterGenerationContext,
        normalized_tags: Sequence[str],
    ) -> GeneratedClan | None:
        family = get_family_config(clan.family_id)
        if family is None:
            return None
        variant_ids = [member.variant_key for member in clan.members if member.variant_key in family.variants]
        if not variant_ids:
            return None

        flavor = await self._build_flavor(family, context, variant_ids, normalized_tags)
        clan.flavor_content = flavor
        clan.name_ru = str(flavor["name_ru"])
        clan.description = str(flavor["description"])
        for member in clan.members:
            variant_flavor = _variant_flavor(flavor, member.variant_key)
            if not variant_flavor:
                continue
            member.name_ru = str(variant_flavor.get("name") or member.name_ru)
            member.description = str(_variant_appearance(variant_flavor) or member.description)
        return clan

    async def build_clan_with_members(
        self,
        family_id: str,
        context: MonsterGenerationContext,
        context_hash: str,
        unique_hash: str,
        normalized_tags: Sequence[str],
    ) -> tuple[GeneratedClan, list[GeneratedMonster]]:
        family = get_family_config(family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {family_id}")

        variant_ids = get_available_variants_for_tier_window(family_id, context.tier)
        if not variant_ids:
            raise ValueError(f"No monster variants for family={family_id} tier={context.tier}")

        flavor = await self._build_flavor(family, context, variant_ids, normalized_tags)
        clan = GeneratedClan(
            id=uuid.uuid4(),
            family_id=family.id,
            tier=context.tier,
            zone_id=context.zone_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            raw_tags={"tags": list(normalized_tags), "biome_id": context.biome_id, "difficulty": context.difficulty},
            flavor_content=flavor,
            name_ru=str(flavor["name_ru"]),
            description=str(flavor["description"]),
        )
        members = [
            self._build_member(clan.id, family, family.variants[variant_id], context.tier, flavor)
            for variant_id in variant_ids
        ]
        clan.members.extend(members)
        for member in members:
            member.clan = clan
            member.combat_seed = build_monster_combat_seed(member)
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

    async def _build_flavor(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        variant_ids: Sequence[str],
        normalized_tags: Sequence[str],
    ) -> dict[str, object]:
        if self.text_ai is not None:
            generated = await self.text_ai.generate_clan_flavor(
                self._build_flavor_prompt_payload(family, context, variant_ids, normalized_tags)
            )
            if generated is not None and self._has_all_variant_flavor(generated.variants_flavor, variant_ids):
                return generated.model_dump(mode="json")

        return self._build_fallback_flavor(family, context, variant_ids)

    def _build_flavor_prompt_payload(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        variant_ids: Sequence[str],
        normalized_tags: Sequence[str],
    ) -> dict[str, object]:
        units_with_roles = {
            variant_id: f"[{family.variants[variant_id].role.title()}] {family.variants[variant_id].narrative_hint}"
            for variant_id in variant_ids
        }
        return {
            "family_id": family.id,
            "archetype": family.archetype,
            "organization": family.organization_type,
            "family_tags": family.default_tags,
            "context_tags": list(normalized_tags),
            "biome_id": context.biome_id,
            "difficulty": context.difficulty,
            "tier": context.tier,
            "units_to_name": units_with_roles,
        }

    @staticmethod
    def _has_all_variant_flavor(variants_flavor: dict[str, object], variant_ids: Sequence[str]) -> bool:
        return all(variant_id in variants_flavor for variant_id in variant_ids)

    def _build_fallback_flavor(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        variant_ids: Sequence[str],
    ) -> dict[str, object]:
        habitat = _HABITAT_NAMES.get(context.biome_id, context.biome_id.replace("_", " "))
        pressure = _DIFFICULTY_NAMES.get(context.difficulty, "active")
        title = _FAMILY_PUBLIC_NAMES.get(family.id, family.id.replace("_", " ").title())
        summary = _FAMILY_PUBLIC_SUMMARIES.get(
            family.id,
            f"A {family.organization_type} of {family.archetype} creatures recorded around {habitat}.",
        )
        return {
            "name_ru": title,
            "description": f"{summary} Scouts rate their presence as {pressure} in {habitat}.",
            "variants_flavor": {
                variant_id: {
                    "name": family.variants[variant_id].id.replace("_", " ").title(),
                    "appearance": family.variants[variant_id].narrative_hint,
                    "encounter": "The creature moves into view, watching for weakness.",
                    "behavior": "It keeps to the clan's hunting pattern.",
                }
                for variant_id in variant_ids
            },
        }

    def _build_member(
        self,
        clan_id: uuid.UUID,
        family: MonsterFamilyDTO,
        variant: MonsterVariantDTO,
        tier: int,
        flavor: dict[str, object],
    ) -> GeneratedMonster:
        multiplier = TIER_SCALING_CONFIG.get(tier, {"stat_mult": 1.0})["stat_mult"]
        base_stats = variant.base_stats.model_dump()
        variant_flavor = _variant_flavor(flavor, variant.id)
        return GeneratedMonster(
            id=uuid.uuid4(),
            clan_id=clan_id,
            variant_key=variant.id,
            role=variant.role,
            threat_rating=variant.cost,
            name_ru=str(variant_flavor.get("name") or variant.id.replace("_", " ").title()),
            description=str(_variant_appearance(variant_flavor) or variant.narrative_hint),
            scaled_base_stats={key: int(value * multiplier) for key, value in base_stats.items()},
            loadout_ids=variant.fixed_loadout.model_dump(exclude_none=True),
            skills_snapshot=list(variant.skills),
            current_state=None,
        )


_HABITAT_NAMES = {
    "city_ruins": "the ruined city district",
    "forest": "the old forest",
    "wasteland": "the ash wastes",
    "mountains": "the high passes",
    "hills": "the broken hills",
    "grassland": "the open grasslands",
    "badlands": "the badlands",
    "highlands": "the highlands",
}


def _variant_flavor(flavor: dict[str, object], variant_id: str) -> dict[str, object]:
    variants = flavor.get("variants_flavor")
    if not isinstance(variants, dict):
        return {}
    entry = variants.get(variant_id)
    return entry if isinstance(entry, dict) else {}


def _variant_appearance(variant_flavor: dict[str, object]) -> str | None:
    raw_flavor = variant_flavor.get("flavor")
    if isinstance(raw_flavor, dict):
        appearance = raw_flavor.get("appearance")
        return str(appearance) if appearance else None
    appearance = variant_flavor.get("appearance")
    if appearance:
        return str(appearance)
    return None


def _looks_generated_placeholder(value: str) -> bool:
    lowered = value.lower()
    if any(marker in lowered for marker in (" t0", " t1", " t2", " t3", " t4", " t5", " t6", " t7")):
        return True
    return "_" in value


_DIFFICULTY_NAMES = {
    "low": "scattered",
    "mid": "steady",
    "high": "heavy",
}

_FAMILY_PUBLIC_NAMES = {
    "bandit_gang": "Roadside Cutthroats",
    "goblin_tribe": "Gutter Goblins",
    "rat_swarm": "Ruin Rats",
    "wolf_pack": "Ashen Wolves",
}

_FAMILY_PUBLIC_SUMMARIES = {
    "bandit_gang": "Human raiders working broken roads, empty courtyards, and abandoned watch posts.",
    "goblin_tribe": "Small scavengers nesting in cracks of the old district and fighting over whatever they can steal.",
    "rat_swarm": "Disease-bearing vermin moving through cellars, drains, and collapsed alleys.",
    "wolf_pack": "Lean predators drawn to the edge of settled ground, testing prey with feints and circling strikes.",
}
