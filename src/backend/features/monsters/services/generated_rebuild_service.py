from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.features.items.services.generation_service import ItemGenerationService
from src.backend.features.monsters.dto.generated_view import (
    MonsterDataRebuildItemDTO,
    MonsterDataRebuildRequestDTO,
    MonsterDataRebuildResponseDTO,
)
from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, MonsterGenerationContext
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.runtime.generation_builder import MonsterClanGenerationBuilder, _MemberPlan
from src.backend.features.monsters.runtime.generation_fields import build_member_tier
from src.backend.features.monsters.runtime.hashing import normalize_tags
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM


class MonsterGeneratedRebuildService:
    """Rebuilds generated monster mechanics from resource definitions without touching visuals."""

    def __init__(self, *, session: Any, item_generation: Any | None = None) -> None:
        self.session = session
        self.item_generation = item_generation or ItemGenerationService()
        self.gear_score_service = MonsterGearScoreService()

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
            .order_by(GeneratedClanORM.family_id, GeneratedClanORM.tier, GeneratedClanORM.id)
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

        item_requests = builder._build_item_requests(family, plans, clan.unique_hash)
        item_requests = [_with_existing_runtime_item_id(request_item, clan) for request_item in item_requests]
        runtime_items = await builder._generate_runtime_items(item_requests)
        flavor = _flavor_without_visual(clan)

        expected_by_variant = {
            plan.variant.id: builder._build_member_row(
                clan_id=clan.id,
                family=family,
                plan=plan,
                runtime_items=runtime_items,
                flavor=flavor,
                context=context,
                unique_hash=clan.unique_hash,
            )
            for plan in plans
        }

        existing_by_variant = {member.variant_key: member for member in clan.members}
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
        existing_by_variant = {member.variant_key: member for member in clan.members}

        for variant_key, expected in {**outcome.changed, **outcome.created}.items():
            existing = existing_by_variant.get(variant_key)
            if existing is None:
                existing = GeneratedMonsterORM(id=expected.id, clan_id=clan.id)
                clan.members.append(existing)
                self.session.add(existing)
            _copy_member_mechanics(existing, expected)
            self.gear_score_service.apply_monster_gear_score(existing)  # type: ignore[arg-type]
            _flag_member_json(existing)

        if remove_obsolete_members:
            for variant_key in outcome.removed:
                obsolete = existing_by_variant.get(variant_key)
                if obsolete is not None:
                    await self.session.delete(obsolete)

        family = get_family_config(clan.family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {clan.family_id}")

        raw_tags = dict(clan.raw_tags or {})
        raw_tags["schema_version"] = 2
        raw_tags["family_resource_version"] = family.resource_version
        raw_tags["composition"] = sorted(outcome.expected_by_variant)
        raw_tags["rebuild"] = {
            "source": "monster_generated_rebuild_service",
            "preserved_visuals": True,
        }
        clan.raw_tags = raw_tags
        clan.biome_id = _context_from_clan(clan).biome_id
        clan.generation_version = max(int(getattr(clan, "generation_version", 1) or 1), 2)
        self.gear_score_service.apply_clan_summary(clan)  # type: ignore[arg-type]
        flag_modified(clan, "raw_tags")


@dataclass(slots=True)
class _ClanRebuildOutcome:
    expected_by_variant: dict[str, Any]
    changed: dict[str, Any]
    created: dict[str, Any]
    removed: set[str]
    reason: str


class _NoopMonsterRepository:
    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClan | None:
        return None

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        return []

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None:
        return None

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        return []

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

    async def update_clan_flavor(self, clan: GeneratedClan) -> GeneratedClan:
        return clan


def _context_from_clan(clan: GeneratedClanORM) -> MonsterGenerationContext:
    raw_tags = dict(clan.raw_tags or {})
    return MonsterGenerationContext(
        zone_id=clan.zone_id,
        biome_id=str(getattr(clan, "biome_id", None) or raw_tags.get("biome_id") or "wasteland"),
        tier=max(0, min(7, int(clan.tier or 0))),
        tags=list(raw_tags.get("tags") or normalize_tags(raw_tags)),
        difficulty=str(raw_tags.get("difficulty") or "mid"),
        context_meta=dict(raw_tags.get("context_meta") or {}),
    )


def _stable_member_id(clan: GeneratedClanORM, variant_key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"monster:{clan.unique_hash}:{variant_key}")


def _stable_member_owner_key(clan: GeneratedClanORM, variant_key: str) -> str:
    return str(_stable_member_id(clan, variant_key))


def _reuse_existing_identity(plan: _MemberPlan, clan: GeneratedClanORM) -> _MemberPlan:
    existing = next((member for member in clan.members if member.variant_key == plan.variant.id), None)
    if existing is None:
        return plan
    meta = dict(existing.generation_meta or {})
    owner_key = str(meta.get("owner_key") or existing.id)
    return _MemberPlan(
        member_id=existing.id,
        owner_key=owner_key,
        variant=plan.variant,
        member_model=plan.member_model,
        member_tier=plan.member_tier,
    )


def _with_existing_runtime_item_id(request_item: Any, clan: GeneratedClanORM) -> Any:
    owner_key = str(request_item.runtime_metadata.get("owner_key") or "")
    slot = str(request_item.target_slot or "")
    existing = next(
        (
            member
            for member in clan.members
            if str(dict(member.generation_meta or {}).get("owner_key") or member.id) == owner_key
        ),
        None,
    )
    if existing is None:
        return request_item
    equipment = dict(dict(existing.items or {}).get("layout", {}).get("equipment", {}))
    item_id = equipment.get(slot)
    if not item_id:
        return request_item
    metadata = {**dict(request_item.runtime_metadata), "runtime_item_id": str(item_id)}
    return request_item.model_copy(update={"runtime_metadata": metadata})


def _flavor_without_visual(clan: GeneratedClanORM) -> dict[str, object]:
    flavor = dict(clan.flavor_content or {})
    flavor.pop("visual", None)
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
    generation_meta = dict(getattr(member, "generation_meta", {}) or {})
    return {
        "variant_key": getattr(member, "variant_key", ""),
        "schema_version": _optional_int(generation_meta.get("schema_version")),
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
    visual = dict((target.generation_meta or {}).get("visual") or {})
    text_content = dict(target.text_content or {}) or dict(expected.text_content)
    generation_meta = dict(expected.generation_meta)
    if visual:
        generation_meta["visual"] = visual

    target.variant_key = expected.variant_key
    target.role = expected.role
    target.member_tier = expected.member_tier
    target.threat_rating = expected.threat_rating
    target.name_ru = target.name_ru or expected.name_ru
    target.description = target.description or expected.description
    target.text_content = text_content
    target.scaled_attributes = dict(expected.scaled_attributes)
    target.scaled_skills = dict(expected.scaled_skills)
    target.items = dict(expected.items)
    target.vitals = dict(expected.vitals)
    target.ai_profile = dict(expected.ai_profile)
    target.generation_meta = generation_meta
    target.combat_actor_snapshot = dict(expected.combat_actor_snapshot)


def _flag_member_json(member: GeneratedMonsterORM) -> None:
    for field_name in (
        "text_content",
        "scaled_attributes",
        "scaled_skills",
        "items",
        "vitals",
        "ai_profile",
        "generation_meta",
        "combat_actor_snapshot",
    ):
        flag_modified(member, field_name)


__all__ = ["MonsterGeneratedRebuildService"]
