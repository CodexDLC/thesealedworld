from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.integrations.item_generation import (
    build_monster_item_request,
    to_item_generation_requests,
)
from src.backend.features.monsters.resources import (
    get_available_variants_for_tier,
    get_family_config,
)
from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS
from src.backend.features.monsters.resources.spawn_config import BIOME_FAMILIES, TIER_AVAILABILITY
from src.backend.features.monsters.runtime.generation_fields import (
    build_generated_monster_template,
    build_member_tier,
)
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, RuntimeItemProjectionDTO
    from src.backend.features.monsters.dto.generation import MonsterGenerationContext
    from src.backend.features.monsters.dto.resources import (
        MonsterFamilyDTO,
        MonsterMemberResourceModelDTO,
        MonsterVariantDTO,
    )
    from src.backend.features.monsters.integrations import MonsterClanTextAIClient, MonsterGenerationStorage


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
        text_ai: MonsterClanTextAIClient | None = None,
    ) -> None:
        self.repository = repository
        self.item_generation = item_generation
        self.text_ai = text_ai

    async def generate_active_clan(
        self,
        context: MonsterGenerationContext,
        *,
        family_id: str | None = None,
        target_budget: float | None = None,
        max_members: int = 12,
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

        budget = self._target_budget(context, target_budget)
        member_plans = self._build_member_plans(family, context, budget, max_members)
        item_requests = self._build_item_requests(family, member_plans, resolved_unique_hash)
        runtime_items = await self._generate_runtime_items(item_requests)
        flavor = await self._build_flavor(family, context, member_plans, tags)
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
                "tags": tags,
                "biome_id": context.biome_id,
                "difficulty": context.difficulty,
                "target_budget": budget,
                "composition": [plan.variant.id for plan in member_plans],
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
        return await self.repository.create_clan_with_members(clan, members)

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
        return candidates[int(context_hash[:8], 16) % len(candidates)]

    def _build_member_plans(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
        target_budget: float,
        max_members: int,
    ) -> list[_MemberPlan]:
        available = [
            variant for variant in family.variants.values() if variant.min_tier <= context.tier <= variant.max_tier
        ]
        if not available:
            raise ValueError(f"No monster variants for family={family.id} tier={context.tier}")

        profile = family.clan_model.balance.composition_profile if family.clan_model else "balanced"
        selected = (
            self._compose_many_weak(family, available, context, target_budget, max_members)
            if "many" in profile or family.organization_type in {"swarm", "horde"}
            else self._compose_balanced(family, available, context, target_budget, max_members)
        )
        plans: list[_MemberPlan] = []
        for variant in selected:
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

    def _compose_many_weak(
        self,
        family: MonsterFamilyDTO,
        available: list[MonsterVariantDTO],
        context: MonsterGenerationContext,
        target_budget: float,
        max_members: int,
    ) -> list[MonsterVariantDTO]:
        minions = self._role_variants(available, "minion")
        veterans = self._role_variants(available, "veteran")
        selected: list[MonsterVariantDTO] = []
        remaining = target_budget
        cheapest_minion_cost = self._effective_cost(family, minions[0]) if minions else 0.0
        if veterans and remaining >= self._effective_cost(family, veterans[0]) + cheapest_minion_cost:
            selected.append(self._pick(veterans, context, len(selected)))
            remaining -= self._effective_cost(family, selected[-1])
        while minions and len(selected) < max_members and remaining >= cheapest_minion_cost:
            selected.append(self._pick(minions, context, len(selected)))
            remaining -= self._effective_cost(family, selected[-1])
        if not selected:
            selected.append(self._pick(minions or available, context, 0))
        return selected

    def _compose_balanced(
        self,
        family: MonsterFamilyDTO,
        available: list[MonsterVariantDTO],
        context: MonsterGenerationContext,
        target_budget: float,
        max_members: int,
    ) -> list[MonsterVariantDTO]:
        selected: list[MonsterVariantDTO] = []
        remaining = target_budget
        ordered = sorted(
            available, key=lambda variant: (self._effective_cost(family, variant), variant.id), reverse=True
        )
        cheapest = min(self._effective_cost(family, variant) for variant in available)
        while len(selected) < max_members and remaining >= cheapest:
            affordable = [variant for variant in ordered if self._effective_cost(family, variant) <= remaining]
            if not affordable:
                break
            selected.append(self._pick(affordable, context, len(selected)))
            remaining -= self._effective_cost(family, selected[-1])
        if not selected:
            selected.append(self._pick(available, context, 0))
        return selected

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
        variant_ids = sorted({plan.variant.id for plan in member_plans})
        if self.text_ai is not None:
            generated = await self.text_ai.generate_clan_flavor(
                self._build_flavor_prompt_payload(family, context, variant_ids, normalized_tags)
            )
            if generated is not None and all(variant_id in generated.variants_flavor for variant_id in variant_ids):
                return generated.model_dump(mode="json")
        return self._build_fallback_flavor(family, context, member_plans)

    @staticmethod
    def _build_flavor_prompt_payload(
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
            "text_contract": {
                "clan": ["name_ru", "description"],
                "member": ["name", "appearance", "detected", "ambush", "idle", "encounter", "behavior"],
                "encounter_states": {
                    "detected": "player noticed the monster first",
                    "ambush": "monster noticed or attacked first",
                    "idle": "monster is observed before combat starts",
                },
            },
            "units_to_name": units_with_roles,
        }

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
        old_stats = _legacy_stats_from_template(template.scaled_attributes.model_dump())
        return GeneratedMonster(
            id=plan.member_id,
            clan_id=clan_id,
            variant_key=plan.variant.id,
            role=plan.variant.role,
            threat_rating=template.balance.threat_rating,
            name_ru=template.text_content.name_ru or plan.variant.id,
            description=template.text_content.appearance_ru or plan.variant.narrative_hint,
            scaled_base_stats=old_stats,
            loadout_ids=template.items.model_dump(mode="json"),
            skills_snapshot=template.scaled_skills.model_dump(mode="json"),
            combat_seed={
                "schema_version": 2,
                "generated_template": template.model_dump(mode="json"),
            },
            current_state=None,
        )

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
    def _target_budget(context: MonsterGenerationContext, target_budget: float | None) -> float:
        if target_budget is not None:
            return max(1.0, float(target_budget))
        if context.threat is not None:
            return max(1.0, float(context.threat))
        return float(max(1, context.count) * 20)

    @staticmethod
    def _effective_cost(family: MonsterFamilyDTO, variant: MonsterVariantDTO) -> float:
        divisor = family.clan_model.balance.organization_divisor if family.clan_model else 1.0
        return max(1.0, round(variant.cost / divisor, 4))

    @staticmethod
    def _role_variants(variants: list[MonsterVariantDTO], role: str) -> list[MonsterVariantDTO]:
        return sorted(
            (variant for variant in variants if variant.role == role), key=lambda variant: (variant.cost, variant.id)
        )

    @staticmethod
    def _pick(variants: list[MonsterVariantDTO], context: MonsterGenerationContext, index: int) -> MonsterVariantDTO:
        ordered = sorted(variants, key=lambda variant: variant.id)
        seed = f"{context.biome_id}:{context.tier}:{context.difficulty}:{index}"
        return ordered[int(uuid.uuid5(uuid.NAMESPACE_DNS, seed).hex[:8], 16) % len(ordered)]

    @staticmethod
    def _item_kind(slot: str, equipment_key: str) -> str:
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


def _string_mapping(value: dict[str, object]) -> dict[str, str]:
    return {str(key): str(raw) for key, raw in value.items() if raw}


def _legacy_stats_from_template(attributes: dict[str, int]) -> dict[str, int]:
    return {
        "strength": int(attributes.get("strength", 0)),
        "agility": int(attributes.get("agility", 0)),
        "endurance": int(attributes.get("endurance", 0)),
        "intelligence": int(attributes.get("intellect", 0)),
        "wisdom": int(attributes.get("memory", 0)),
        "men": int(attributes.get("mental", 0)),
        "perception": int(attributes.get("perception", 0)),
        "charisma": int(attributes.get("projection", 0)),
        "luck": int(attributes.get("prediction", 0)),
    }


_NATURAL_DEFAULT_LOADOUTS: dict[str, dict[str, str]] = {
    "rat_swarm": {"main_hand": "rat_bite_claws", "chest_armor": "rat_light_hide"},
    "wolf_pack": {"main_hand": "wolf_bite_claws", "chest_armor": "wolf_hide"},
}
