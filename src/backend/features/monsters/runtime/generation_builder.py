from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO
from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.dto.loot_culture import default_loot_culture_payload
from src.backend.features.monsters.integrations.item_generation import (
    build_monster_item_request,
    to_item_generation_requests,
)
from src.backend.features.monsters.resources import (
    get_available_variants_for_family_tier,
    get_family_config,
)
from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS
from src.backend.features.monsters.resources.spawn_config import BIOME_FAMILIES, TIER_AVAILABILITY
from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.runtime.generation_fields import (
    build_generated_monster_template,
    build_member_tier,
)
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.features.monsters.tasks_ai import build_monster_clan_flavor_task_spec

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.generation_ai import GenerationAIService
    from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, RuntimeItemProjectionDTO
    from src.backend.features.monsters.dto.generation import MonsterGenerationContext
    from src.backend.features.monsters.dto.resources import (
        MonsterFamilyDTO,
        MonsterMemberResourceModelDTO,
        MonsterVariantDTO,
    )
    from src.backend.features.monsters.integrations import MonsterGenerationStorage


@dataclass(frozen=True, slots=True)
class _MemberPlan:
    member_id: uuid.UUID
    owner_key: str
    variant: MonsterVariantDTO
    member_model: MonsterMemberResourceModelDTO | None
    member_tier: int


class MonsterClanGenerationBuilder:
    def __init__(
        self,
        *,
        repository: MonsterGenerationStorage,
        item_generation,
        generation_ai: GenerationAIService | None = None,
    ) -> None:
        self.repository = repository
        self.item_generation = item_generation
        self.generation_ai = generation_ai
        self.gear_score_service = MonsterGearScoreService()

    async def generate_active_clan(
        self,
        context: MonsterGenerationContext,
        *,
        family_id: str | None = None,
        context_hash: str | None = None,
        unique_hash: str | None = None,
        normalized_tags: Sequence[str] | None = None,
        reuse_existing: bool = True,
    ) -> GeneratedClan:
        return await self.generate_clan_template(
            context,
            family_id=family_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=normalized_tags,
            reuse_existing=reuse_existing,
        )

    async def generate_clan_template(
        self,
        context: MonsterGenerationContext,
        *,
        family_id: str | None = None,
        context_hash: str | None = None,
        unique_hash: str | None = None,
        normalized_tags: Sequence[str] | None = None,
        reuse_existing: bool = True,
    ) -> GeneratedClan:
        tags = list(normalized_tags or normalize_tags(context.tags))
        resolved_context_hash = context_hash or compute_context_hash(context.tier, context.biome_id, tags)
        resolved_family_id = family_id or self.select_family_id(context, resolved_context_hash)
        if resolved_family_id is None:
            raise ValueError(f"No monster families available for biome={context.biome_id} tier={context.tier}")

        family = get_family_config(resolved_family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {resolved_family_id}")

        resolved_unique_hash = unique_hash or compute_unique_clan_hash(family.id, resolved_context_hash)
        if reuse_existing:
            existing = await self.repository.get_clan_by_unique_hash(resolved_unique_hash)
            if existing is not None:
                return existing

        member_plans = self._build_member_plans(family, context)
        item_requests = self._build_item_requests(family, member_plans, resolved_unique_hash)
        runtime_items = await self._generate_runtime_items(item_requests)
        flavor = await self._build_flavor(family, context, member_plans, tags)
        flavor = {
            **flavor,
            "visual": build_clan_visual(
                family.id,
                clan_name=str(flavor["name_ru"]),
                description=str(flavor["description"]),
                context_tags=list(tags),
            ),
        }
        clan_id = uuid.uuid4()
        clan = GeneratedClan(
            id=clan_id,
            family_id=family.id,
            tier=context.tier,
            zone_id=context.zone_id,
            context_hash=resolved_context_hash,
            unique_hash=resolved_unique_hash,
            raw_tags={
                "schema_version": 2,
                "family_resource_version": family.resource_version,
                "tags": tags,
                "biome_id": context.biome_id,
                "difficulty": context.difficulty,
                "variant_window": {"min_tier": 0, "max_tier": min(7, context.tier + 1)},
                "composition": [plan.variant.id for plan in member_plans],
                "context_meta": context.context_meta,
            },
            flavor_content=flavor,
            name_ru=str(flavor["name_ru"]),
            description=str(flavor["description"]),
        )
        members = [
            self._build_member_row(
                clan_id=clan_id,
                family=family,
                plan=plan,
                runtime_items=runtime_items,
                flavor=flavor,
                context=context,
                unique_hash=resolved_unique_hash,
            )
            for plan in member_plans
        ]
        clan.members.extend(members)
        for member in members:
            member.clan = clan
        created = await self.repository.create_clan_with_members(clan, members)
        await self._enqueue_ai_flavor(created)
        return created

    def get_available_family_ids(self, context: MonsterGenerationContext) -> list[str]:
        candidates = sorted(self._select_candidates(context.tier, context.biome_id))
        family_bias = self._family_bias_from_tags(context.tags)
        if family_bias:
            candidates = [family_id for family_id in candidates if family_id in family_bias]
        return [
            family_id
            for family_id in candidates
            if get_family_config(family_id) is not None
            and get_available_variants_for_family_tier(family_id, context.tier)
        ]

    def select_family_id(self, context: MonsterGenerationContext, context_hash: str) -> str | None:
        candidates = self.get_available_family_ids(context)
        if not candidates:
            return None
        return candidates[int(context_hash[:8], 16) % len(candidates)]

    def _build_member_plans(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
    ) -> list[_MemberPlan]:
        max_variant_tier = min(7, context.tier + 1)
        available = [
            variant
            for variant in family.variants.values()
            if variant.min_tier <= max_variant_tier and variant.max_tier >= 0
        ]
        if not available:
            raise ValueError(f"No monster variants for family={family.id} tier={context.tier}")

        plans: list[_MemberPlan] = []
        for variant in sorted(available, key=lambda item: (item.min_tier, item.role, item.cost, item.id)):
            member_model = self._member_model_for(family, variant)
            member_id = uuid.uuid4()
            plans.append(
                _MemberPlan(
                    member_id=member_id,
                    owner_key=str(member_id),
                    variant=variant,
                    member_model=member_model,
                    member_tier=build_member_tier(context.tier, variant, member_model),
                )
            )
        return plans

    def _build_item_requests(
        self,
        family: MonsterFamilyDTO,
        member_plans: list[_MemberPlan],
        unique_hash: str,
    ) -> list[ItemGenerationRequestDTO]:
        monster_requests = []
        for plan in member_plans:
            for slot, equipment_key in self._member_loadout(family, plan).items():
                is_natural = equipment_key in NATURAL_EQUIPMENT_MAPPINGS
                monster_requests.append(
                    build_monster_item_request(
                        owner_key=plan.owner_key,
                        family_id=family.id,
                        member_role=plan.variant.role,
                        member_tier=plan.member_tier,
                        slot=slot,
                        natural_key=equipment_key if is_natural else None,
                        base_id=None if is_natural else equipment_key,
                        item_kind=self._item_kind(slot, equipment_key),
                        seed=f"{unique_hash}:{plan.owner_key}:{slot}",
                        source_context={
                            "variant_key": plan.variant.id,
                            "slot": slot,
                        },
                    )
                )
        return to_item_generation_requests(monster_requests)

    async def _generate_runtime_items(
        self, item_requests: list[ItemGenerationRequestDTO]
    ) -> list[RuntimeItemProjectionDTO]:
        if not item_requests:
            return []
        return list(await self.item_generation.generate_runtime_projections(item_requests))

    async def _build_flavor(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        member_plans: list[_MemberPlan],
        normalized_tags: Sequence[str],
    ) -> dict[str, object]:
        return self._build_fallback_flavor(family, context, member_plans)

    async def _enqueue_ai_flavor(self, clan: GeneratedClan) -> None:
        if self.generation_ai is None:
            return
        await self.generation_ai.enqueue_many([build_monster_clan_flavor_task_spec(clan)])

    def _build_member_row(
        self,
        *,
        clan_id: uuid.UUID,
        family: MonsterFamilyDTO,
        plan: _MemberPlan,
        runtime_items: list[RuntimeItemProjectionDTO],
        flavor: dict[str, object],
        context: MonsterGenerationContext,
        unique_hash: str,
    ) -> GeneratedMonster:
        variant_flavor = _variant_flavor(flavor, plan.variant.id)
        template = build_generated_monster_template(
            family,
            plan.variant,
            context_tier=context.tier,
            owner_key=plan.owner_key,
            member_model=plan.member_model,
            runtime_items=runtime_items,
            generated_text=variant_flavor,
            source={
                "clan_unique_hash": unique_hash,
                "owner_key": plan.owner_key,
            },
        )
        member = GeneratedMonster(
            id=plan.member_id,
            clan_id=clan_id,
            variant_key=plan.variant.id,
            role=plan.variant.role,
            member_tier=template.member_tier,
            threat_rating=template.balance.threat_rating,
            name_ru=template.text_content.name_ru or plan.variant.id,
            description=template.text_content.appearance_ru or plan.variant.narrative_hint,
            text_content=template.text_content.model_dump(mode="json"),
            scaled_attributes=template.scaled_attributes.model_dump(mode="json"),
            scaled_skills=template.scaled_skills.model_dump(mode="json")["skills"],
            items=template.items.model_dump(mode="json"),
            vitals=_build_vitals(
                template.scaled_attributes.model_dump(mode="json"),
                profile_key=f"monster:{family.archetype}",
            ),
            ai_profile=template.ai_profile.model_dump(mode="json"),
            generation_meta={
                "schema_version": 2,
                "family_resource_version": family.resource_version,
                "source": "monster_clan_generation_builder",
                "clan_unique_hash": unique_hash,
                "owner_key": plan.owner_key,
                "visual": build_member_visual(
                    family.id,
                    variant_key=plan.variant.id,
                    role=plan.variant.role,
                    member_name=template.text_content.name_ru or plan.variant.id,
                    appearance=template.text_content.appearance_ru or plan.variant.narrative_hint,
                ),
                "balance": template.balance.model_dump(mode="json"),
                "meta": template.meta.model_dump(mode="json"),
                "family_modifiers": template.family_modifiers,
            },
        )
        self.gear_score_service.apply_monster_gear_score(member)
        return member

    def _member_loadout(self, family: MonsterFamilyDTO, plan: _MemberPlan) -> dict[str, str]:
        if plan.member_model and plan.member_model.item_loadout_profile:
            return _string_mapping(plan.member_model.item_loadout_profile)
        fixed = plan.variant.fixed_loadout.model_dump(exclude_none=True)
        if fixed:
            return _string_mapping(fixed)
        return dict(_NATURAL_DEFAULT_LOADOUTS.get(family.id, {}))

    @staticmethod
    def _member_model_for(family: MonsterFamilyDTO, variant: MonsterVariantDTO) -> MonsterMemberResourceModelDTO | None:
        if variant.member_model is not None:
            return variant.member_model
        for member_model in family.member_models:
            if member_model.variant_key == variant.id:
                return member_model
        return None

    @staticmethod
    def _select_candidates(tier: int, biome_id: str) -> set[str]:
        in_biome = set(BIOME_FAMILIES.get(biome_id, set()))
        in_tier = set(TIER_AVAILABILITY.get(tier, set()))
        if "all_families" in in_tier:
            return in_biome
        candidates = in_biome & in_tier
        if candidates:
            return candidates
        return in_tier - {"all_families"}

    @staticmethod
    def _family_bias_from_tags(tags: Sequence[str]) -> set[str]:
        starter_families = {"rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe"}
        return set(tags) & starter_families

    @staticmethod
    def _item_kind(slot: str, equipment_key: str) -> str:
        if slot == "quiver" or equipment_key.startswith("quiver_"):
            return "ammo"
        if equipment_key in {"shield", "buckler"}:
            return "shield"
        if slot in {"main_hand", "off_hand", "two_hand"}:
            return "weapon"
        return "armor"

    @staticmethod
    def _build_fallback_flavor(
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        member_plans: list[_MemberPlan],
    ) -> dict[str, object]:
        title = family.id.replace("_", " ").title()
        return {
            "name_ru": f"{title} T{context.tier}",
            "description": f"{family.organization_type} generated for {context.biome_id} at tier {context.tier}.",
            "loot_culture": _fallback_loot_culture(family),
            "variants_flavor": {
                plan.variant.id: {
                    "name": plan.variant.id.replace("_", " ").title(),
                    "appearance": plan.variant.narrative_hint,
                    "detected": plan.variant.narrative_hint,
                    "ambush": plan.variant.narrative_hint,
                    "idle": plan.variant.narrative_hint,
                    "encounter": plan.variant.narrative_hint,
                    "behavior": plan.variant.role,
                }
                for plan in member_plans
            },
        }


def _variant_flavor(flavor: dict[str, object], variant_id: str) -> dict[str, object]:
    variants = flavor.get("variants_flavor")
    if not isinstance(variants, dict):
        return {}
    entry = variants.get(variant_id)
    return entry if isinstance(entry, dict) else {}


def _fallback_loot_culture(family: MonsterFamilyDTO) -> dict[str, object]:
    return default_loot_culture_payload(
        family_id=family.id,
        archetype=family.archetype,
        organization_type=family.organization_type,
    )


def _string_mapping(value: dict[str, object]) -> dict[str, str]:
    return {str(key): str(raw) for key, raw in value.items() if raw}


def _build_vitals(attributes: dict[str, int], *, profile_key: str) -> dict[str, object]:
    dto = CharacterSessionAttributesDTO.model_validate(attributes)
    return CharacterVitalsCalculator.build_initial_vitals(dto, profile_key=profile_key).model_dump(mode="json")


_NATURAL_DEFAULT_LOADOUTS: dict[str, dict[str, str]] = {
    "rat_swarm": {"main_hand": "rat_bite_claws", "chest_armor": "rat_light_hide"},
    "wolf_pack": {"main_hand": "wolf_bite_claws", "chest_armor": "wolf_hide"},
}
