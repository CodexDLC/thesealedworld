from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.core.calculators.stats_waterfall_calculator import COMBAT_MATH_VERSION
from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
from src.backend.features.character.runtime.combat_math_model import COMBAT_MODIFIER_KEYS, MODIFIER_ALIASES
from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO
from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO
from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
from src.backend.features.monsters.integrations.item_generation import (
    build_monster_item_request,
    to_item_generation_requests,
)
from src.backend.features.monsters.resources import (
    get_family_config,
)
from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS
from src.backend.features.monsters.resources.traits import (
    MONSTER_CLAN_TRAIT_CATALOG_VERSION,
    select_monster_clan_traits_for_habitat,
    serialize_selected_trait,
)
from src.backend.features.monsters.resources.visuals import build_clan_visual, build_member_visual
from src.backend.features.monsters.runtime.ai_archetype import resolve_monster_ai_archetype
from src.backend.features.monsters.runtime.combat_math_model import MonsterCombatMathModelBuilder
from src.backend.features.monsters.runtime.generation_fields import (
    build_generated_monster_template,
    build_member_tier,
)
from src.backend.features.monsters.runtime.hashing import (
    compute_clan_identity_hash,
    compute_habitat_hash,
)
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.features.monsters.tasks_ai import build_monster_clan_flavor_task_spec
from src.backend.infrastructure.monsters.actor_documents import (
    GENERATED_MONSTER_ACTOR_KIND,
    GENERATED_MONSTER_ACTOR_SNAPSHOT_VERSION,
)

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
        self.combat_math = MonsterCombatMathModelBuilder()

    async def generate_active_clan(
        self,
        context: MonsterGenerationContext,
        *,
        family_id: str | None = None,
        context_hash: str | None = None,
        identity_hash: str | None = None,
        unique_hash: str | None = None,
        normalized_tags: Sequence[str] | None = None,
        reuse_existing: bool = True,
    ) -> GeneratedClan:
        return await self.generate_clan_template(
            context,
            family_id=family_id,
            context_hash=context_hash,
            identity_hash=identity_hash,
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
        identity_hash: str | None = None,
        unique_hash: str | None = None,
        normalized_tags: Sequence[str] | None = None,
        reuse_existing: bool = True,
    ) -> GeneratedClan:
        if context.tier < 1:
            raise ValueError(f"Generated monster clan tier must be >= 1, got {context.tier}")

        habitat_biome = context.habitat_biome
        habitat_keys = list(context.habitat_keys)
        tags = list(normalized_tags or habitat_keys)
        resolved_context_hash = context_hash or compute_habitat_hash(biome=habitat_biome, keys=habitat_keys)
        resolved_family_id = family_id
        if resolved_family_id is None:
            raise ValueError("Monster clan generation requires an explicit family_id from a habitat clan pool")

        family = get_family_config(resolved_family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {resolved_family_id}")

        selected_traits = [
            serialize_selected_trait(trait)
            for trait in select_monster_clan_traits_for_habitat(
                family,
                biome_id=habitat_biome,
                habitat_keys=habitat_keys,
            )
        ]
        selected_trait_keys = [str(trait["key"]) for trait in selected_traits]
        resolved_identity_hash = (
            identity_hash
            or unique_hash
            or compute_clan_identity_hash(
                family_id=family.id,
                biome=habitat_biome,
                keys=habitat_keys,
                selected_trait_keys=selected_trait_keys,
                generation_version=2,
                resource_version=family.resource_version,
            )
        )
        if reuse_existing:
            existing = await self.repository.get_clan_by_identity_hash(resolved_identity_hash)
            if existing is not None:
                return existing

        member_plans = self._build_member_plans(family, context)
        item_requests = self._build_item_requests(family, member_plans, resolved_identity_hash)
        runtime_items = await self._generate_runtime_items(item_requests)
        flavor = await self._build_flavor(family, context, member_plans, tags)
        flavor = {
            **flavor,
            "traits": selected_traits,
            "visual": build_clan_visual(
                family.id,
                clan_name=str(flavor["name_ru"]),
                description=str(flavor["description"]),
                context_tags=[habitat_biome, *habitat_keys],
            ),
        }
        clan_id = uuid.uuid4()
        context_identity = {
            "schema_version": 2,
            "combat_math_version": COMBAT_MATH_VERSION,
            "family_resource_version": family.resource_version,
            "tags": tags,
            "biome_id": context.biome_id,
            "difficulty": context.difficulty,
            "trait_catalog_version": MONSTER_CLAN_TRAIT_CATALOG_VERSION,
            "selected_traits": selected_traits,
            "habitat": {"biome": habitat_biome, "keys": habitat_keys},
            "variant_window": {"min_tier": 0, "max_tier": 7},
            "composition": [plan.variant.id for plan in member_plans],
            "context_meta": context.context_meta,
            "tier": context.tier,
            "zone_id": context.zone_id,
        }
        clan = GeneratedClan(
            id=clan_id,
            family_id=family.id,
            identity_hash=resolved_identity_hash,
            context_identity=context_identity,
            context_hash=resolved_context_hash,
            selected_traits=selected_traits,
            title=str(flavor["name_ru"]),
            description=str(flavor["description"]),
            encounter_texts=_string_mapping(flavor.get("encounter_texts")),
            generation_version=2,
            resource_version=str(family.resource_version),
            metadata_={"visual": flavor["visual"]},
        )
        members = [
            self._build_member_row(
                clan_id=clan_id,
                family=family,
                plan=plan,
                runtime_items=runtime_items,
                flavor=flavor,
                context=context,
                identity_hash=resolved_identity_hash,
                selected_traits=selected_traits,
            )
            for plan in member_plans
        ]
        clan.members.extend(members)
        for member in members:
            member.clan = clan
        created = await self.repository.create_clan_with_members(clan, members)
        await self._enqueue_ai_flavor(created)
        return created

    def _build_member_plans(
        self,
        family: MonsterFamilyDTO,
        context: MonsterGenerationContext,
    ) -> list[_MemberPlan]:
        available = [variant for variant in family.variants.values() if self._snapshot_tiers(family, variant)]
        if not available:
            raise ValueError(f"No monster variants for family={family.id} tier={context.tier}")

        plans: list[_MemberPlan] = []
        for variant in sorted(available, key=lambda item: (item.min_tier, item.role, item.spawn_weight, item.id)):
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
        identity_hash: str,
    ) -> list[ItemGenerationRequestDTO]:
        monster_requests = []
        for plan in member_plans:
            for snapshot_tier in self._snapshot_tiers(family, plan.variant):
                tier_owner_key = _tier_owner_key(plan.owner_key, snapshot_tier)
                for slot, equipment_key in self._member_loadout(family, plan).items():
                    is_natural = equipment_key in NATURAL_EQUIPMENT_MAPPINGS
                    monster_requests.append(
                        build_monster_item_request(
                            owner_key=tier_owner_key,
                            family_id=family.id,
                            member_role=plan.variant.role,
                            member_tier=snapshot_tier,
                            slot=slot,
                            natural_key=equipment_key if is_natural else None,
                            base_id=None if is_natural else equipment_key,
                            item_kind=self._item_kind(slot, equipment_key),
                            seed=f"{identity_hash}:{plan.owner_key}:tier:{snapshot_tier}:{slot}",
                            source_context={
                                "variant_id": plan.variant.id,
                                "slot": slot,
                                "effective_tier": snapshot_tier,
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
        del family, member_plans, normalized_tags
        raw_flavor = context.context_meta.get("clan_flavor")
        if raw_flavor is None:
            raise ValueError("Monster clan generation requires clan_flavor in context_meta")
        return MonsterClanFlavorDTO.model_validate(raw_flavor).model_dump_with_variant_mapping()

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
        identity_hash: str,
        selected_traits: list[dict[str, object]],
    ) -> GeneratedMonster:
        del flavor
        variant_flavor = {
            "name_ru": plan.variant.id.replace("_", " ").title(),
            "short_name_ru": plan.variant.id.replace("_", " ").title(),
            "appearance_ru": plan.variant.narrative_hint,
        }
        snapshot_tiers = self._snapshot_tiers(family, plan.variant)
        active_tier = self._active_snapshot_tier(family, plan.variant, requested_tier=context.tier)
        active_template = None
        tier_snapshots: dict[str, dict[str, object]] = {}
        for snapshot_tier in snapshot_tiers:
            template = build_generated_monster_template(
                family,
                plan.variant,
                context_tier=snapshot_tier,
                owner_key=_tier_owner_key(plan.owner_key, snapshot_tier),
                member_model=plan.member_model,
                runtime_items=runtime_items,
                generated_text=variant_flavor,
                source={
                    "clan_identity_hash": identity_hash,
                    "owner_key": plan.owner_key,
                    "effective_tier": snapshot_tier,
                },
            )
            tier_snapshots[_tier_key(snapshot_tier)] = self._build_tier_snapshot(
                clan_id=clan_id,
                family=family,
                plan=plan,
                template=template,
                selected_traits=selected_traits,
                snapshot_tier=snapshot_tier,
                identity_hash=identity_hash,
            )
            if snapshot_tier == active_tier:
                active_template = template
        if active_template is None:
            raise ValueError(f"No active tier snapshot for family={family.id} variant={plan.variant.id}")

        text_content = active_template.text_content.model_dump(mode="json")
        active_snapshot = dict(tier_snapshots[_tier_key(active_tier)])
        member = GeneratedMonster(
            id=plan.member_id,
            clan_id=clan_id,
            variant_id=plan.variant.id,
            member_hash=plan.owner_key,
            role=plan.variant.role,
            title=active_template.text_content.name_ru or plan.variant.id,
            short_description=active_template.text_content.appearance_ru or plan.variant.narrative_hint,
            min_tier=min(snapshot_tiers),
            max_tier=max(snapshot_tiers),
            mongo_actor_key=f"actor:{clan_id}:{plan.variant.id}:{plan.owner_key}",
            active_snapshot=active_snapshot,
            metadata_={
                "schema_version": 2,
                "combat_math_version": COMBAT_MATH_VERSION,
                "family_resource_version": family.resource_version,
                "source": "monster_clan_generation_builder",
                "clan_identity_hash": identity_hash,
                "owner_key": plan.owner_key,
                "visual": build_member_visual(
                    family.id,
                    variant_key=plan.variant.id,
                    role=plan.variant.role,
                    member_name=active_template.text_content.name_ru or plan.variant.id,
                    appearance=active_template.text_content.appearance_ru or plan.variant.narrative_hint,
                    context_tags=[context.habitat_biome, *context.habitat_keys],
                ),
                "meta": active_template.meta.model_dump(mode="json"),
            },
        )
        member.actor_document = _build_actor_document(
            clan_id=clan_id,
            family_id=family.id,
            member=member,
            resource_version=str(family.resource_version),
            selected_traits=selected_traits,
            tier_snapshots=tier_snapshots,
            base_text_content=text_content,
            base_loadout=self._member_loadout(family, plan),
        )
        return member

    def _build_tier_snapshot(
        self,
        *,
        clan_id: uuid.UUID,
        family: MonsterFamilyDTO,
        plan: _MemberPlan,
        template: Any,
        selected_traits: list[dict[str, object]],
        snapshot_tier: int,
        identity_hash: str,
    ) -> dict[str, object]:
        attributes = template.scaled_attributes.model_dump(mode="json")
        skills = template.scaled_skills.model_dump(mode="json")["skills"]
        items = template.items.model_dump(mode="json")
        balance = template.balance.model_dump(mode="json")
        meta = template.meta.model_dump(mode="json")
        vitals = _build_vitals(attributes, profile_key=f"monster:{family.archetype}")
        combat_input = self._build_combat_snapshot_input(
            clan_id=clan_id,
            family=family,
            plan=plan,
            attributes=attributes,
            skills=skills,
            items=items,
            vitals=vitals,
            balance=balance,
            meta=meta,
            selected_traits=selected_traits,
            snapshot_tier=snapshot_tier,
            identity_hash=identity_hash,
        )
        raw_gear_score = CharacterGearScoreCalculator.calculate_from_raw(
            dict(combat_input["raw"]),
            skills=dict(combat_input["skills"]),
            loadout=dict(combat_input["loadout"]),
        )
        return {
            "schema_version": GENERATED_MONSTER_ACTOR_SNAPSHOT_VERSION,
            "snapshot_tier": snapshot_tier,
            "effective_tier": snapshot_tier,
            "member_tier": template.member_tier,
            "text_content": template.text_content.model_dump(mode="json"),
            "scaled_attributes": attributes,
            "scaled_skills": skills,
            "attributes": attributes,
            "skills": skills,
            "loadout": dict(combat_input["loadout"]),
            "items": items,
            "vitals": vitals,
            "ai_profile": template.ai_profile.model_dump(mode="json"),
            "balance": balance,
            "meta": meta,
            "affixes": _item_affixes(items),
            "raw_gear_score": raw_gear_score,
            "gear_score": raw_gear_score,
            "assembly_cost": _assembly_cost(raw_gear_score, balance),
            "gear_score_version": MonsterGearScoreService.VERSION,
            "combat_snapshot_input": combat_input,
        }

    def _build_combat_snapshot_input(
        self,
        *,
        clan_id: uuid.UUID,
        family: MonsterFamilyDTO,
        plan: _MemberPlan,
        attributes: dict[str, Any],
        skills: dict[str, Any],
        items: dict[str, Any],
        vitals: dict[str, Any],
        balance: dict[str, Any],
        meta: dict[str, Any],
        selected_traits: list[dict[str, object]],
        snapshot_tier: int,
        identity_hash: str,
    ) -> dict[str, Any]:
        flat_skills = {str(key): float(value or 0.0) for key, value in skills.items()}
        mapped_items = _items_for_player_mapper(items)
        loadout = CharacterCombatActorInputBuilder._loadout(
            mapped_items, flat_skills, include_basic_gift_abilities=False
        )
        monster_meta = {
            **meta,
            "family_id": family.id,
            "archetype": family.archetype,
            "role": plan.variant.role,
            "organization_type": family.organization_type,
            "tags": [family.id, family.archetype, *family.default_tags, *plan.variant.extra_tags],
        }
        raw = self.combat_math.build_raw(
            attributes=attributes,
            items=mapped_items,
            skills=flat_skills,
            monster_meta=monster_meta,
            balance=balance,
        )
        _apply_selected_trait_modifiers(raw, selected_traits, effective_tier=snapshot_tier)
        return {
            "meta": {
                "actor_type": "monster",
                "actor_id": str(plan.member_id),
                "name": str(meta.get("name") or plan.variant.id),
                "role": plan.variant.role,
                "family_id": family.id,
                "variant_id": plan.variant.id,
                "snapshot_tier": snapshot_tier,
                "effective_tier": snapshot_tier,
                "archetype": family.archetype,
                "organization_type": family.organization_type,
                "ai_archetype": resolve_monster_ai_archetype(plan.variant.id, family.archetype, plan.variant.role),
                "tags": sorted(
                    {family.id, family.archetype, plan.variant.role, *family.default_tags, *plan.variant.extra_tags}
                ),
            },
            "source": {
                "monster_id": str(plan.member_id),
                "clan_id": str(clan_id),
                "family_id": family.id,
                "variant_id": plan.variant.id,
                "member_hash": plan.owner_key,
                "mongo_actor_key": f"actor:{clan_id}:{plan.variant.id}:{plan.owner_key}",
                "identity_hash": identity_hash,
            },
            "status": vitals,
            "raw": raw,
            "skills": flat_skills,
            "loadout": loadout,
        }

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
    def _item_kind(slot: str, equipment_key: str) -> str:
        mapping = NATURAL_EQUIPMENT_MAPPINGS.get(equipment_key)
        if mapping is not None:
            return mapping.item_kind
        if slot == "quiver" or equipment_key.startswith("quiver_"):
            return "ammo"
        if slot == "amulet":
            return "accessory"
        if equipment_key in {"shield", "buckler"}:
            return "shield"
        if slot in {"main_hand", "off_hand", "two_hand"}:
            return "weapon"
        return "armor"

    @staticmethod
    def _snapshot_tiers(family: MonsterFamilyDTO, variant: MonsterVariantDTO) -> list[int]:
        family_range = family.clan_model.tier_range if family.clan_model is not None else None
        family_min = family_range.min_tier if family_range is not None else 1
        family_max = family_range.max_tier if family_range is not None else 7
        min_tier = max(1, int(family_min), int(variant.min_tier))
        max_tier = min(7, int(family_max), int(variant.max_tier))
        return list(range(min_tier, max_tier + 1)) if min_tier <= max_tier else []

    def _active_snapshot_tier(
        self, family: MonsterFamilyDTO, variant: MonsterVariantDTO, *, requested_tier: int
    ) -> int:
        tiers = self._snapshot_tiers(family, variant)
        if not tiers:
            raise ValueError(f"No tier snapshots for family={family.id} variant={variant.id}")
        if requested_tier in tiers:
            return requested_tier
        return min(tiers, key=lambda tier: (abs(tier - requested_tier), tier))


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(raw) for key, raw in value.items() if raw}


def _build_vitals(attributes: dict[str, int], *, profile_key: str) -> dict[str, object]:
    dto = CharacterSessionAttributesDTO.model_validate(attributes)
    return CharacterVitalsCalculator.build_initial_vitals(dto, profile_key=profile_key).model_dump(mode="json")


def _build_actor_document(
    *,
    clan_id: uuid.UUID,
    family_id: str,
    member: GeneratedMonster,
    resource_version: str,
    selected_traits: list[dict[str, object]],
    tier_snapshots: dict[str, dict[str, object]],
    base_text_content: dict[str, object],
    base_loadout: dict[str, str],
) -> dict[str, object]:
    return {
        "document_kind": GENERATED_MONSTER_ACTOR_KIND,
        "schema_version": 1,
        "snapshot_version": GENERATED_MONSTER_ACTOR_SNAPSHOT_VERSION,
        "combat_math_version": COMBAT_MATH_VERSION,
        "family_resource_version": resource_version,
        "trait_catalog_version": MONSTER_CLAN_TRAIT_CATALOG_VERSION,
        "gear_score_version": MonsterGearScoreService.VERSION,
        "clan_id": str(clan_id),
        "family_id": family_id,
        "variant_id": member.variant_id,
        "member_id": str(member.id),
        "member_hash": member.member_hash,
        "mongo_actor_key": member.mongo_actor_key,
        "resource_version": resource_version,
        "base_projection": {
            "family_id": family_id,
            "variant_id": member.variant_id,
            "selected_traits_applied": list(selected_traits),
            "title": member.title,
            "short_description": member.short_description,
            "role": member.role,
            "text_content": base_text_content,
            "base_loadout": base_loadout,
            "visual": dict(member.metadata_.get("visual") or {}),
        },
        "tier_snapshots": {str(key): dict(value) for key, value in tier_snapshots.items()},
    }


def _items_for_player_mapper(items: dict[str, Any]) -> dict[str, Any]:
    layout = dict(items.get("layout") or {})
    by_id = dict(items.get("by_id") or {})
    return {
        "layout": dict(layout),
        "by_id": {str(item_id): _runtime_item_for_player_mapper(raw) for item_id, raw in by_id.items()},
    }


def _runtime_item_for_player_mapper(raw: Any) -> dict[str, Any]:
    item = dict(raw) if isinstance(raw, dict) else {}
    combat = dict(item.get("combat") or {})
    generation = dict(item.get("generation") or {})
    result = {
        **item,
        **combat,
        "item_id": str(item.get("item_id") or ""),
        "base_id": str(item.get("base_id") or combat.get("base_id") or ""),
        "item_type": str(item.get("item_type") or combat.get("item_type") or ""),
        "type": str(item.get("item_type") or combat.get("item_type") or ""),
        "slot": str(item.get("slot") or ""),
        "rarity_tier": item.get("rarity_tier", generation.get("rarity_tier", 0)),
        "affixes": list(generation.get("affixes") or []),
    }
    mechanics = dict(result.get("mechanics") or {})
    mechanics.update(combat)
    result["mechanics"] = mechanics
    return result


def _item_affixes(items: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = dict(items.get("by_id") or {})
    affixes: list[dict[str, Any]] = []
    for item_id, raw in by_id.items():
        item = dict(raw) if isinstance(raw, dict) else {}
        generation = dict(item.get("generation") or {})
        for affix in generation.get("affixes") or []:
            if isinstance(affix, dict):
                affixes.append({"item_id": str(item_id), **affix})
    return affixes


def _apply_selected_trait_modifiers(
    raw: dict[str, Any], traits: list[dict[str, object]], *, effective_tier: int
) -> None:
    modifiers = raw.setdefault("modifiers", {})
    if not isinstance(modifiers, dict):
        return
    for trait in traits:
        trait_key = str(trait.get("key") or "").strip()
        entries = trait.get("modifiers")
        if not trait_key or not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            target = str(entry.get("target") or "")
            key = MODIFIER_ALIASES.get(target, target)
            if key not in COMBAT_MODIFIER_KEYS:
                continue
            value = round(_float(entry.get("base")) + _float(entry.get("per_tier")) * max(0, int(effective_tier)), 4)
            modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
            source = modifiers[key].setdefault("source", {})
            if isinstance(source, dict):
                source[f"clan_trait:{trait_key}"] = value


def _tier_key(value: int) -> str:
    return f"tier_{int(value)}"


def _tier_owner_key(owner_key: str, tier: int) -> str:
    return f"{owner_key}:tier:{int(tier)}"


def _float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _assembly_cost(raw_gear_score: int, balance: dict[str, Any]) -> int:
    divisor = max(1.0, _float(balance.get("organization_divisor"), default=1.0))
    return max(1, round(float(raw_gear_score) / divisor))


_NATURAL_DEFAULT_LOADOUTS: dict[str, dict[str, str]] = {
    "rat_swarm": {"main_hand": "rat_bite_claws", "chest_armor": "rat_light_hide"},
    "wolf_pack": {"main_hand": "wolf_bite_claws", "chest_armor": "wolf_hide"},
}
