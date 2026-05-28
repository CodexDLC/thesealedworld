from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto.generation import (
    GeneratedClan,
    GeneratedMonster,
    MonsterGenerationContext,
    MonsterGroupMemberPreview,
    MonsterGroupResult,
)
from src.backend.features.monsters.resources import get_available_variants_for_family_tier, get_family_config
from src.backend.features.monsters.resources.visuals import version_generated_asset_url, version_visual_image_urls
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler
from src.backend.features.monsters.runtime.hashing import compute_context_hash, compute_unique_clan_hash, normalize_tags
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService

if TYPE_CHECKING:
    from src.backend.features.monsters.integrations import (
        MonsterActorCommitmentIntegration,
        MonsterGenerationStorage,
        MonsterLocationContextIntegration,
    )
    from src.backend.features.monsters.runtime.clan_factory import ClanFactory
    from src.backend.infrastructure.monsters.managers import MonsterGroupCacheManager


class MonsterGroupService:
    def __init__(
        self,
        *,
        repository: MonsterGenerationStorage,
        location_context: MonsterLocationContextIntegration,
        actor_commitments: MonsterActorCommitmentIntegration,
        group_cache: MonsterGroupCacheManager | None = None,
        factory: ClanFactory,
        assembler: MonsterGroupAssembler | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repository = repository
        self.location_context = location_context
        self.actor_commitments = actor_commitments
        self.group_cache = group_cache
        self.factory = factory
        self.assembler = assembler or MonsterGroupAssembler()
        self.actor_builder = MonsterCombatActorInputBuilder()
        self.gear_score_service = MonsterGearScoreService()
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
        composition_policy: dict[str, Any] | None = None,
    ) -> MonsterGroupResult:
        location = await self.location_context.get_location_context(loc_id)
        context = MonsterGenerationContext(
            zone_id=location.zone_id,
            biome_id=location.biome_id,
            tier=location.tier,
            tags=location.tags,
            difficulty="mid",
            context_meta=self._context_meta(location.raw_location),
        )
        normalized_tags = normalize_tags(context.tags)
        context_hash = compute_context_hash(context.tier, context.biome_id, normalized_tags)
        clan, reused_existing_clan = await self._resolve_clan(
            context,
            context_hash,
            normalized_tags,
            preferred_family_id,
        )
        return await self._prepare_group_from_clan(
            clan=clan,
            budget=budget,
            tier=location.tier,
            danger=location.danger,
            loc_id=location.loc_id,
            zone_id=location.zone_id,
            biome_id=location.biome_id,
            context_hash=context_hash,
            tags=list(normalized_tags),
            reused_existing_clan=reused_existing_clan,
            force_single_family=force_single_family,
            composition_policy=composition_policy,
            scope_id=scope_id,
            ttl=ttl,
        )

    async def prepare_monster_group_from_clan(
        self,
        clan_id: uuid.UUID | str,
        budget: float,
        *,
        tier: int,
        danger: float,
        biome_id: str,
        loc_id: str,
        zone_id: str | None = None,
        tags: list[str] | None = None,
        force_single_family: bool = True,
        composition_policy: dict[str, Any] | None = None,
        scope_id: str | None = None,
        ttl: int = 300,
    ) -> MonsterGroupResult:
        clan = await self.repository.get_generated_clan(clan_id)
        if clan is None:
            raise ValueError(f"Generated monster clan not found: {clan_id}")

        return await self._prepare_group_from_clan(
            clan=clan,
            budget=budget,
            tier=tier,
            danger=danger,
            loc_id=loc_id,
            zone_id=zone_id,
            biome_id=biome_id,
            context_hash=clan.context_hash,
            tags=list(tags or []),
            reused_existing_clan=True,
            force_single_family=force_single_family,
            composition_policy=composition_policy,
            scope_id=scope_id,
            ttl=ttl,
        )

    async def _prepare_group_from_clan(
        self,
        *,
        clan: GeneratedClan,
        budget: float,
        tier: int,
        danger: float,
        loc_id: str,
        zone_id: str | None,
        biome_id: str,
        context_hash: str,
        tags: list[str],
        reused_existing_clan: bool,
        force_single_family: bool,
        composition_policy: dict[str, Any] | None,
        scope_id: str | None,
        ttl: int,
    ) -> MonsterGroupResult:
        members = await self._fresh_clan_members(clan.id)
        for member in members:
            if member.clan is None:
                member.clan = clan
        assembly = self.assembler.assemble(
            members,
            budget=budget,
            tier=tier,
            danger=danger,
            force_single_family=force_single_family,
            composition_policy=composition_policy,
        )
        if not assembly.members:
            raise ValueError(f"No generated monsters available for clan={clan.id}")

        group_id = scope_id or f"monster_group:{uuid.uuid4()}"
        sources = [self._materialize_actor_source(member) for member in assembly.members]
        actor_commitments = await self.actor_commitments.save_monster_sources(
            sources=sources,
            ttl=ttl,
        )
        expected_source_refs = {f"monster:{source['source']['monster_id']}" for source in sources}
        if set(actor_commitments) != expected_source_refs:
            raise RuntimeError("Failed to save all monster actor commitments")

        previews = [self._preview(member) for member in assembly.members]
        result = MonsterGroupResult(
            group_id=group_id,
            clan_id=str(clan.id),
            family_id=clan.family_id,
            loc_id=loc_id,
            zone_id=zone_id,
            biome_id=biome_id,
            tier=tier,
            danger=danger,
            target_budget=assembly.target_budget,
            adjusted_budget=assembly.adjusted_budget,
            total_power=assembly.total_power,
            monster_ids=[str(member.id) for member in assembly.members],
            actor_commitments=actor_commitments,
            previews=previews,
            reused_existing_clan=reused_existing_clan,
            context_hash=context_hash,
            unique_hash=clan.unique_hash,
            tags=tags,
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

        clan = await self.factory.build_clan_template(
            context=context,
            family_id=family_id,
            context_hash=context_hash,
            unique_hash=unique_hash,
            normalized_tags=normalized_tags,
        )
        return clan, False

    async def _fresh_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        refresh = getattr(self.repository, "refresh_clan_gear_scores", None)
        if callable(refresh):
            return await refresh(clan_id, gear_score_service=self.gear_score_service)
        members = await self.repository.get_clan_members(clan_id)
        self.gear_score_service.refresh_stale_monster_scores(members)
        return members

    def _validate_preferred_family(self, context: MonsterGenerationContext, family_id: str) -> None:
        family = get_family_config(family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {family_id}")
        available = set(self.factory.get_available_family_ids(context))
        if family_id not in available or not get_available_variants_for_family_tier(family_id, context.tier):
            raise ValueError(
                f"Monster family is not available for biome={context.biome_id} tier={context.tier}: {family_id}"
            )

    def _choose_existing_clan(self, clans: list[GeneratedClan]) -> GeneratedClan:
        return self._rng.choice(sorted(clans, key=lambda clan: clan.unique_hash))

    @staticmethod
    def _context_meta(raw_location: dict) -> dict[str, object]:
        flags = raw_location.get("flags")
        if not isinstance(flags, dict):
            return {}
        rift_profile = flags.get("rift_profile")
        return {"rift_profile": rift_profile} if isinstance(rift_profile, dict) else {}

    def _materialize_actor_source(self, monster: GeneratedMonster) -> dict[str, object]:
        return self.actor_builder.build_snapshot(monster)

    def _preview(self, monster: GeneratedMonster) -> MonsterGroupMemberPreview:
        family_id = monster.family_id
        family = get_family_config(family_id) if family_id else None
        tags = ["monster", monster.role]
        if family is not None:
            tags.extend([family.id, family.archetype, *family.default_tags])
        visual = version_visual_image_urls(self._monster_visual(monster))
        return MonsterGroupMemberPreview(
            monster_id=str(monster.id),
            name=monster.name_ru,
            description=monster.description,
            detected_ru=self._variant_text(monster, "detected"),
            ambush_ru=self._variant_text(monster, "ambush"),
            idle_ru=self._variant_text(monster, "idle"),
            role=monster.role,
            variant_key=monster.variant_key,
            member_tier=monster.member_tier,
            threat_rating=monster.threat_rating,
            hp=dict((monster.vitals or {}).get("hp") or {}),
            image=self._visual_image_url(visual),
            visual=visual,
            tags=sorted(set(tags)),
            archetype=family.archetype if family is not None else None,
            family_id=family_id,
            organization_type=self._organization_type(monster, family=family),
            gear_score=self._gear_score(monster),
            vitals=self._preview_vitals(monster),
            equipment=self._preview_equipment(monster),
            affixes=self._preview_affixes(monster),
        )

    @staticmethod
    def _monster_visual(monster: GeneratedMonster) -> dict[str, Any]:
        meta = dict(monster.generation_meta or {})
        visual = meta.get("visual")
        return dict(visual) if isinstance(visual, dict) else {}

    @staticmethod
    def _visual_image_url(visual: dict[str, Any]) -> str | None:
        for key in ("image_url", "generated_image_url", "fallback_image_url"):
            value = visual.get(key)
            if value:
                return version_generated_asset_url(str(value), visual)
        return None

    @staticmethod
    def _organization_type(monster: GeneratedMonster, *, family: Any | None) -> str | None:
        balance = dict((monster.generation_meta or {}).get("balance") or {})
        value = balance.get("organization_type")
        if value:
            return str(value)
        return str(family.organization_type) if family is not None else None

    @staticmethod
    def _gear_score(monster: GeneratedMonster) -> int | None:
        balance = dict((monster.generation_meta or {}).get("balance") or {})
        value = balance.get("gear_score")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _preview_vitals(monster: GeneratedMonster) -> dict[str, Any]:
        raw = dict(monster.vitals or {})
        return {
            "hp": dict(raw.get("hp") or {}),
            "energy": dict(raw.get("energy") or raw.get("en") or {}),
            "concentration": dict(raw.get("concentration") or raw.get("stamina") or {}),
        }

    @staticmethod
    def _preview_equipment(monster: GeneratedMonster) -> list[dict[str, Any]]:
        items = dict(monster.items or {})
        layout = dict(items.get("layout") or {})
        equipment = dict(layout.get("equipment") or {})
        by_id = dict(items.get("by_id") or {})
        rows: list[dict[str, Any]] = []
        for slot, item_id in equipment.items():
            item = by_id.get(str(item_id))
            if not isinstance(item, dict):
                continue
            combat = dict(item.get("combat") or {})
            rows.append(
                {
                    "slot": str(slot),
                    "kind": str(item.get("item_type") or "item"),
                    "label": str(item.get("base_id") or item_id),
                    "item_id": str(item_id),
                    "tags": [str(tag) for tag in combat.get("tags", []) if tag]
                    if isinstance(combat.get("tags"), list)
                    else [],
                }
            )
        return rows

    @staticmethod
    def _preview_affixes(monster: GeneratedMonster) -> list[dict[str, Any]]:
        items = dict(monster.items or {})
        by_id = dict(items.get("by_id") or {})
        affixes: list[dict[str, Any]] = []
        for item in by_id.values():
            if not isinstance(item, dict):
                continue
            generation = dict(item.get("generation") or {})
            raw_affixes = generation.get("affixes")
            if isinstance(raw_affixes, list):
                affixes.extend(dict(affix) for affix in raw_affixes if isinstance(affix, dict))
        return affixes

    @staticmethod
    def _variant_text(monster: GeneratedMonster, key: str) -> str:
        clan = monster.clan
        if clan is None:
            return ""
        variants = clan.flavor_content.get("variants_flavor")
        if not isinstance(variants, dict):
            return ""
        flavor = variants.get(monster.variant_key)
        if not isinstance(flavor, dict):
            return ""
        nested = flavor.get("flavor")
        if isinstance(nested, dict):
            value = nested.get(key)
            if value:
                return str(value)
        value = flavor.get(key)
        return str(value) if value else ""

    @staticmethod
    def _group_payload(result: MonsterGroupResult) -> dict[str, object]:
        return result.model_dump(mode="json", exclude={"group_key"})
