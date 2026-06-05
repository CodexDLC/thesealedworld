from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.core.calculators.stats_waterfall_calculator import COMBAT_MATH_VERSION
from src.backend.features.items.services.generation_service import ItemGenerationService
from src.backend.features.monsters.dto.generated_view import (
    MonsterDataRebuildItemDTO,
    MonsterDataRebuildRequestDTO,
    MonsterDataRebuildResponseDTO,
)
from src.backend.features.monsters.dto.generation import (
    GeneratedClan,
    GeneratedMonster,
    HabitatClanPoolEntryDTO,
    MonsterGenerationContext,
    MonsterHabitatDTO,
)
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder, _MemberPlan
from src.backend.features.monsters.runtime.generation_fields import build_member_tier
from src.backend.features.monsters.runtime.hashing import normalize_tags
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM
from src.backend.infrastructure.monsters.actor_documents import GeneratedMonsterActorRepository


class MonsterGeneratedRebuildService:
    """Rebuilds generated monster mechanics from resource definitions without touching visuals."""

    def __init__(self, *, session: Any, item_generation: Any | None = None) -> None:
        self.session = session
        self.item_generation = item_generation or ItemGenerationService()
        self.gear_score_service = MonsterGearScoreService()
        self.actor_repo = GeneratedMonsterActorRepository()

    async def plan(self, request: MonsterDataRebuildRequestDTO) -> MonsterDataRebuildResponseDTO:
        return await self._run(request, dry_run=True)

    async def apply(self, request: MonsterDataRebuildRequestDTO) -> MonsterDataRebuildResponseDTO:
        result = await self._run(request, dry_run=False)
        await self.session.commit()
        return result

    async def _run(
        self,
        request: MonsterDataRebuildRequestDTO,
        *,
        dry_run: bool,
    ) -> MonsterDataRebuildResponseDTO:
        clans = await self._load_clans(request)
        items: list[MonsterDataRebuildItemDTO] = []
        errors: list[str] = []
        rebuilt = 0
        stale = 0
        skipped = 0

        for clan in clans:
            try:
                outcome = await self._plan_clan(clan, request)
            except ValueError as exc:
                errors.append(str(exc))
                skipped += 1
                continue

            is_stale = bool(request.force or outcome.changed or outcome.created or outcome.removed)
            if is_stale:
                stale += 1
            else:
                skipped += 1

            if is_stale and not dry_run:
                await self._apply_clan(clan, outcome, remove_obsolete_members=request.remove_obsolete_members)
                rebuilt += 1

            items.append(
                MonsterDataRebuildItemDTO(
                    clan_id=str(clan.id),
                    family_id=clan.family_id,
                    status="stale" if is_stale else "fresh",
                    reason=outcome.reason,
                    members_expected=len(outcome.expected_by_variant),
                    members_changed=len(outcome.changed),
                    members_created=len(outcome.created),
                    members_removed=len(outcome.removed) if request.remove_obsolete_members else 0,
                )
            )

        return MonsterDataRebuildResponseDTO(
            dry_run=dry_run,
            status="ok" if not errors else "partial",
            scanned=len(clans),
            stale=stale,
            rebuilt=rebuilt,
            skipped=skipped,
            errors=errors,
            items=items,
        )

    async def _load_clans(self, request: MonsterDataRebuildRequestDTO) -> list[GeneratedClanORM]:
        stmt = (
            select(GeneratedClanORM)
            .options(selectinload(GeneratedClanORM.members))
            .order_by(GeneratedClanORM.family_id, GeneratedClanORM.identity_hash, GeneratedClanORM.id)
            .limit(request.limit)
        )
        if request.clan_id:
            stmt = stmt.where(GeneratedClanORM.id == uuid.UUID(str(request.clan_id)))
        if request.family_id:
            stmt = stmt.where(GeneratedClanORM.family_id == request.family_id)
        return list((await self.session.scalars(stmt)).all())

    async def _plan_clan(
        self,
        clan: GeneratedClanORM,
        request: MonsterDataRebuildRequestDTO,
    ) -> _ClanRebuildOutcome:
        family = get_family_config(clan.family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {clan.family_id}")

        context = _context_from_clan(clan)
        builder = MonsterClanGenerationBuilder(
            repository=_NoopMonsterRepository(),
            item_generation=self.item_generation,
        )
        base_plans = builder._build_member_plans(family, context)
        plans = [
            _MemberPlan(
                member_id=_stable_member_id(clan, plan.variant.id),
                owner_key=_stable_member_owner_key(clan, plan.variant.id),
                variant=plan.variant,
                member_model=plan.member_model,
                member_tier=build_member_tier(context.tier, plan.variant, plan.member_model),
            )
            for plan in base_plans
        ]
        plans = [_reuse_existing_identity(plan, clan) for plan in plans]

        identity_hash = str(clan.identity_hash)
        item_requests = builder._build_item_requests(family, plans, identity_hash)
        item_requests = [_with_existing_runtime_item_id(request_item, clan) for request_item in item_requests]
        runtime_items = await builder._generate_runtime_items(item_requests)
        flavor = _flavor_without_visual(clan)
        selected_traits = list(clan.selected_traits or [])

        expected_by_variant = {
            plan.variant.id: builder._build_member_row(
                clan_id=clan.id,
                family=family,
                plan=plan,
                runtime_items=runtime_items,
                flavor=flavor,
                context=context,
                identity_hash=identity_hash,
                selected_traits=selected_traits,
            )
            for plan in plans
        }

        existing_by_variant = {member.variant_id: member for member in clan.members}
        changed: dict[str, Any] = {}
        created: dict[str, Any] = {}
        removed = set(existing_by_variant) - set(expected_by_variant)

        for variant_key, expected in expected_by_variant.items():
            existing = existing_by_variant.get(variant_key)
            if existing is None:
                created[variant_key] = expected
                continue
            if request.force or _rebuild_version_payload(existing) != _rebuild_version_payload(expected):
                changed[variant_key] = expected

        reasons = []
        if changed:
            reasons.append(f"changed={len(changed)}")
        if created:
            reasons.append(f"created={len(created)}")
        if removed and request.remove_obsolete_members:
            reasons.append(f"removed={len(removed)}")

        return _ClanRebuildOutcome(
            expected_by_variant=expected_by_variant,
            changed=changed,
            created=created,
            removed=removed,
            reason=", ".join(reasons),
        )

    async def _apply_clan(
        self,
        clan: GeneratedClanORM,
        outcome: _ClanRebuildOutcome,
        *,
        remove_obsolete_members: bool,
    ) -> None:
        existing_by_variant = {member.variant_id: member for member in clan.members}

        for variant_key, expected in {**outcome.changed, **outcome.created}.items():
            existing = existing_by_variant.get(variant_key)
            if existing is None:
                existing = GeneratedMonsterORM(id=expected.id, clan_id=clan.id)
                clan.members.append(existing)
                self.session.add(existing)
            _copy_member_mechanics(existing, expected)
            _flag_member_json(existing)
            actor_document = _actor_document_for_apply(existing, expected)
            mongo_document_id = await self.actor_repo.upsert_actor_document(actor_document)
            existing.mongo_document_id = mongo_document_id
            existing.mongo_status = "stored"

        if remove_obsolete_members:
            for variant_key in outcome.removed:
                obsolete = existing_by_variant.get(variant_key)
                if obsolete is not None:
                    await self.session.delete(obsolete)

        family = get_family_config(clan.family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {clan.family_id}")

        context_identity = dict(clan.context_identity or {})
        context_identity["schema_version"] = 2
        context_identity["combat_math_version"] = COMBAT_MATH_VERSION
        context_identity["family_resource_version"] = family.resource_version
        context_identity["composition"] = sorted(outcome.expected_by_variant)
        context_identity["rebuild"] = {
            "source": "monster_generated_rebuild_service",
            "preserved_visuals": True,
        }
        context_identity["gear_score_summary"] = self.gear_score_service.build_clan_summary(
            list(outcome.expected_by_variant.values())
        )
        clan.context_identity = context_identity
        clan.generation_version = max(int(getattr(clan, "generation_version", 1) or 1), 2)
        clan.resource_version = str(family.resource_version)
        flag_modified(clan, "context_identity")


@dataclass(slots=True)
class _ClanRebuildOutcome:
    expected_by_variant: dict[str, Any]
    changed: dict[str, Any]
    created: dict[str, Any]
    removed: set[str]
    reason: str


class _NoopMonsterRepository:
    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        return None

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        return []

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None:
        return None

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        return []

    async def list_habitat_clan_pool_entries(
        self,
        *,
        scope_type: str,
        scope_id: str,
        enabled_only: bool = True,
    ) -> list[HabitatClanPoolEntryDTO]:
        return []

    async def upsert_habitat_clan_pool_entry(self, entry: HabitatClanPoolEntryDTO) -> HabitatClanPoolEntryDTO:
        return entry

    async def delete_generated_clans_outside_zone_contexts(
        self,
        expected: dict[str, set[tuple[str, str]]],
    ) -> int:
        return 0

    async def refresh_clan_gear_scores(
        self,
        clan_id: uuid.UUID | str,
        *,
        gear_score_service: MonsterGearScoreService | None = None,
        persist: bool = False,
    ) -> list[GeneratedMonster]:
        return []

    async def create_clan_with_members(self, clan: GeneratedClan, members: list[GeneratedMonster]) -> GeneratedClan:
        raise RuntimeError("Rebuild service must not create clans through the generation repository")

    async def update_clan_narrative(self, clan: GeneratedClan) -> GeneratedClan:
        return clan


def _context_from_clan(clan: GeneratedClanORM) -> MonsterGenerationContext:
    context_identity = dict(clan.context_identity or {})
    habitat = dict(context_identity.get("habitat") or {})
    biome_id = str(context_identity.get("biome_id") or "wasteland")
    tags = list(context_identity.get("tags") or normalize_tags(context_identity))
    return MonsterGenerationContext(
        zone_id=str(context_identity.get("zone_id") or ""),
        biome_id=biome_id,
        tier=max(0, min(7, _optional_int(context_identity.get("tier")) or 0)),
        tags=tags,
        difficulty=str(context_identity.get("difficulty") or "mid"),
        context_meta=dict(context_identity.get("context_meta") or {}),
        habitat=MonsterHabitatDTO(biome=str(habitat.get("biome") or biome_id), keys=list(habitat.get("keys") or tags)),
    )


def _stable_member_id(clan: GeneratedClanORM, variant_key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"monster:{clan.identity_hash}:{variant_key}")


def _stable_member_owner_key(clan: GeneratedClanORM, variant_key: str) -> str:
    return str(_stable_member_id(clan, variant_key))


def _reuse_existing_identity(plan: _MemberPlan, clan: GeneratedClanORM) -> _MemberPlan:
    existing = next((member for member in clan.members if member.variant_id == plan.variant.id), None)
    if existing is None:
        return plan
    meta = dict(existing.metadata_ or {})
    owner_key = str(meta.get("owner_key") or existing.id)
    return _MemberPlan(
        member_id=existing.id,
        owner_key=owner_key,
        variant=plan.variant,
        member_model=plan.member_model,
        member_tier=plan.member_tier,
    )


def _with_existing_runtime_item_id(request_item: Any, clan: GeneratedClanORM) -> Any:
    del clan
    return request_item


def _flavor_without_visual(clan: GeneratedClanORM) -> dict[str, object]:
    metadata = dict(clan.metadata_ or {})
    flavor = dict(metadata.get("flavor_content") or {})
    flavor.pop("visual", None)
    flavor.setdefault("name_ru", clan.title)
    flavor.setdefault("description", clan.description)
    return flavor


def _mechanics_payload(member: Any) -> dict[str, Any]:
    generation_meta = dict(getattr(member, "generation_meta", {}) or {})
    return {
        "variant_key": getattr(member, "variant_key", ""),
        "role": getattr(member, "role", ""),
        "member_tier": int(getattr(member, "member_tier", 0) or 0),
        "threat_rating": int(getattr(member, "threat_rating", 0) or 0),
        "scaled_attributes": dict(getattr(member, "scaled_attributes", {}) or {}),
        "scaled_skills": dict(getattr(member, "scaled_skills", {}) or {}),
        "items": dict(getattr(member, "items", {}) or {}),
        "vitals": dict(getattr(member, "vitals", {}) or {}),
        "ai_profile": dict(getattr(member, "ai_profile", {}) or {}),
        "balance": dict(generation_meta.get("balance") or {}),
        "family_modifiers": list(generation_meta.get("family_modifiers") or []),
    }


def _rebuild_version_payload(member: Any) -> dict[str, Any]:
    generation_meta = dict(getattr(member, "generation_meta", None) or getattr(member, "metadata_", {}) or {})
    return {
        "variant_key": getattr(member, "variant_key", None) or getattr(member, "variant_id", ""),
        "schema_version": _optional_int(generation_meta.get("schema_version")),
        "combat_math_version": str(generation_meta.get("combat_math_version") or ""),
        "family_resource_version": _optional_version(generation_meta.get("family_resource_version")),
    }


def _optional_int(value: object) -> int | None:
    if not isinstance(value, int | str):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _optional_version(value: object) -> str | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        version = Decimal(str(value))
    except InvalidOperation:
        return None
    return format(version.normalize(), "f")


def _copy_member_mechanics(target: GeneratedMonsterORM, expected: Any) -> None:
    visual = dict((target.metadata_ or {}).get("visual") or {})
    metadata = dict(expected.metadata_)
    if visual:
        metadata["visual"] = visual

    target.variant_id = expected.variant_id
    target.member_hash = expected.member_hash
    target.role = expected.role
    target.title = target.title or expected.title
    target.short_description = target.short_description or expected.short_description
    target.min_tier = expected.min_tier
    target.max_tier = expected.max_tier
    target.mongo_actor_key = expected.mongo_actor_key
    target.metadata_ = metadata


def _actor_document_for_apply(target: GeneratedMonsterORM, expected: Any) -> dict[str, Any]:
    document = dict(expected.actor_document)
    base_projection = dict(document.get("base_projection") or {})
    visual = dict((target.metadata_ or {}).get("visual") or {})
    if visual:
        base_projection["visual"] = visual
    base_projection["title"] = target.title or base_projection.get("title") or expected.title
    base_projection["short_description"] = (
        target.short_description or base_projection.get("short_description") or expected.short_description
    )
    document["base_projection"] = base_projection
    return document


def _flag_member_json(member: GeneratedMonsterORM) -> None:
    for field_name in ("metadata_",):
        flag_modified(member, field_name)


__all__ = ["MonsterGeneratedRebuildService"]
