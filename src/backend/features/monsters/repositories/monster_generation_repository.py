from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loguru import logger as log
from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster, HabitatClanPoolEntryDTO
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM, HabitatClanPoolEntryORM, Monster
from src.backend.infrastructure.monsters.actor_documents import (  # type: ignore
    GeneratedMonsterActorRepository,
    MissingGeneratedMonsterActorDocumentError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class MonsterGenerationRepository:
    """Replacement-only persistence adapter for generated monster clans."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.actor_repo = GeneratedMonsterActorRepository()

    async def get_clan_by_identity_hash(self, identity_hash: str) -> GeneratedClan | None:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.identity_hash == identity_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        clan = await self.session.scalar(stmt)
        if clan is None:
            return None
        return await self._to_generated_clan_with_actors(clan)

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_hash == context_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.scalars(stmt)
        return [await self._to_generated_clan_with_actors(clan) for clan in result.all()]

    async def get_generated_clan(self, clan_id: uuid.UUID | str) -> GeneratedClan | None:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == uuid.UUID(str(clan_id)))
            .options(selectinload(GeneratedClanORM.members))
        )
        clan = await self.session.scalar(stmt)
        if clan is None:
            return None
        return await self._to_generated_clan_with_actors(clan)

    async def list_habitat_clan_pool_entries(
        self,
        *,
        scope_type: str,
        scope_id: str,
        enabled_only: bool = True,
    ) -> list[HabitatClanPoolEntryDTO]:
        stmt = (
            select(HabitatClanPoolEntryORM)
            .where(
                HabitatClanPoolEntryORM.scope_type == str(scope_type),
                HabitatClanPoolEntryORM.scope_id == str(scope_id),
            )
            .order_by(
                HabitatClanPoolEntryORM.pool_tier,
                HabitatClanPoolEntryORM.family_id,
                HabitatClanPoolEntryORM.clan_identity_hash,
            )
        )
        if enabled_only:
            stmt = stmt.where(HabitatClanPoolEntryORM.enabled.is_(True))
        result = await self.session.scalars(stmt)
        return [_to_pool_entry(row) for row in result.all()]

    async def upsert_habitat_clan_pool_entry(self, entry: HabitatClanPoolEntryDTO) -> HabitatClanPoolEntryDTO:
        values = {
            "scope_type": entry.scope_type,
            "scope_id": entry.scope_id,
            "clan_identity_hash": entry.clan_identity_hash,
            "family_id": entry.family_id,
            "pool_tier": entry.pool_tier,
            "weight": entry.weight,
            "enabled": entry.enabled,
            "habitat": entry.habitat.model_dump(mode="json"),
            "policy_version": entry.policy_version,
        }
        stmt = pg_insert(HabitatClanPoolEntryORM).values(**values)
        await self.session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_habitat_clan_pool_scope_clan",
                set_={
                    "family_id": stmt.excluded.family_id,
                    "pool_tier": stmt.excluded.pool_tier,
                    "weight": stmt.excluded.weight,
                    "enabled": stmt.excluded.enabled,
                    "habitat": stmt.excluded.habitat,
                    "policy_version": stmt.excluded.policy_version,
                },
            )
        )
        await self.session.flush()
        loaded = await self.session.scalar(
            select(HabitatClanPoolEntryORM).where(
                HabitatClanPoolEntryORM.scope_type == entry.scope_type,
                HabitatClanPoolEntryORM.scope_id == entry.scope_id,
                HabitatClanPoolEntryORM.clan_identity_hash == entry.clan_identity_hash,
            )
        )
        if loaded is None:
            raise RuntimeError("Failed to upsert habitat clan pool entry")
        return _to_pool_entry(loaded)

    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_identity["zone_id"].as_string() == str(zone_id))
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.scalars(stmt)
        return [await self._to_generated_clan_with_actors(clan) for clan in result.all()]

    async def list_generated_clans(self, limit: int = 100) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .options(selectinload(GeneratedClanORM.members))
            .order_by(GeneratedClanORM.family_id, GeneratedClanORM.identity_hash)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return [await self._to_generated_clan_with_actors(clan) for clan in result.all()]

    async def count_generated_clans(
        self,
        *,
        family_id: str | None = None,
        clan_id: uuid.UUID | str | None = None,
    ) -> int:
        stmt = select(func.count(GeneratedClanORM.id))
        stmt = self._filter_clans(stmt, family_id=family_id, clan_id=clan_id)
        return int(await self.session.scalar(stmt) or 0)

    async def list_generated_clans_page(
        self,
        *,
        family_id: str | None = None,
        clan_id: uuid.UUID | str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[GeneratedClan]:
        stmt = (
            select(GeneratedClanORM)
            .options(selectinload(GeneratedClanORM.members))
            .order_by(GeneratedClanORM.family_id, GeneratedClanORM.identity_hash, GeneratedClanORM.id)
            .limit(limit)
            .offset(offset)
        )
        stmt = self._filter_clans(stmt, family_id=family_id, clan_id=clan_id)
        result = await self.session.scalars(stmt)
        return [await self._to_generated_clan_with_actors(clan) for clan in result.all()]

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonster]:
        stmt = (
            select(Monster)
            .where(Monster.clan_id == uuid.UUID(str(clan_id)))
            .options(selectinload(Monster.clan))
            .order_by(Monster.role, Monster.variant_id)
        )
        result = await self.session.scalars(stmt)
        members = list(result.all())
        return await self._to_generated_members_with_actors(members)

    async def require_member_actor_snapshot(self, member_id: uuid.UUID | str, effective_tier: int) -> dict[str, Any]:
        member = await self.session.scalar(select(Monster).where(Monster.id == uuid.UUID(str(member_id))))
        if member is None:
            raise ValueError(f"Generated clan member not found: {member_id}")
        return await self.actor_repo.require_tier_snapshot(member.mongo_actor_key, effective_tier)

    async def delete_generated_clans_outside_zone_contexts(
        self,
        expected: dict[str, set[tuple[str, str]]],
    ) -> int:
        deleted = 0
        for zone_id, family_contexts in expected.items():
            normalized_contexts = {
                (str(family_id), str(context_hash))
                for family_id, context_hash in family_contexts
                if str(family_id).strip() and str(context_hash).strip()
            }
            if not zone_id or not normalized_contexts:
                continue
            result = await self.session.execute(
                delete(GeneratedClanORM).where(
                    GeneratedClanORM.context_identity["zone_id"].as_string() == str(zone_id),
                    tuple_(GeneratedClanORM.family_id, GeneratedClanORM.context_hash).not_in(normalized_contexts),
                )
            )
            deleted += int(getattr(result, "rowcount", 0) or 0)
        return deleted

    async def create_clan_with_members(
        self,
        clan: GeneratedClan,
        members: Sequence[GeneratedMonster],
    ) -> GeneratedClan:
        log.bind(clan_id=str(clan.id), member_count=len(members)).debug("MonsterGenerationClanWithMembersCreated")
        clan_orm = _to_clan_orm(clan)
        member_orms = [_to_monster_orm(member) for member in members]
        clan_orm.members.extend(member_orms)
        self.session.add(clan_orm)
        if hasattr(self.session, "add_all"):
            self.session.add_all(member_orms)
        await self.session.flush()
        await self.sync_actor_documents_for_clan(clan_orm, members=member_orms, source_members=list(members))
        return await self._to_generated_clan_with_actors(clan_orm)

    async def update_clan_narrative(self, clan: GeneratedClan) -> GeneratedClan:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == clan.id)
            .options(selectinload(GeneratedClanORM.members))
        )
        clan_orm = await self.session.scalar(stmt)
        if clan_orm is None:
            raise ValueError(f"Generated clan not found: {clan.id}")

        clan_orm.title = clan.title
        clan_orm.description = clan.description
        clan_orm.encounter_texts = dict(clan.encounter_texts)
        clan_orm.selected_traits = list(clan.selected_traits)
        members_by_id = {member.id: member for member in clan.members}
        for member_orm in clan_orm.members:
            member = members_by_id.get(member_orm.id)
            if member is None:
                continue
            member_orm.title = member.title
            member_orm.short_description = member.short_description

        await self.session.flush()
        await self.sync_actor_documents_for_clan(clan_orm, members=list(clan_orm.members), source_members=clan.members)
        return await self._to_generated_clan_with_actors(clan_orm)

    async def sync_actor_documents_for_clan(
        self,
        clan: GeneratedClanORM,
        *,
        members: Sequence[GeneratedMonsterORM] | None = None,
        source_members: Sequence[GeneratedMonster] | None = None,
    ) -> None:
        rows = list(members if members is not None else getattr(clan, "members", []) or [])
        source_by_id = {member.id: member for member in source_members or []}
        now = datetime.now(UTC)
        try:
            for row in rows:
                source = source_by_id.get(row.id)
                document = dict(source.actor_document) if source is not None else {}
                if not document:
                    raise MissingGeneratedMonsterActorDocumentError(
                        f"Missing generated monster actor document for member={row.id}"
                    )
                row.mongo_document_id = await self.actor_repo.upsert_actor_document(document)
                row.mongo_status = "synced"
                row.mongo_stored_at = now
            clan.mongo_status = "synced"
            clan.mongo_stored_at = now
        except Exception as exc:  # noqa: BLE001
            clan.mongo_status = "error"
            for row in rows:
                row.mongo_status = "error"
            log.warning("GeneratedMonsterActorSyncFailed", clan_id=str(clan.id), error=str(exc))
            raise

    async def _to_generated_clan_with_actors(self, clan: GeneratedClanORM) -> GeneratedClan:
        generated_clan = _to_generated_clan(clan)
        generated_clan.members.extend(
            await self._to_generated_members_with_actors(list(clan.members), clan=generated_clan)
        )
        return generated_clan

    async def _to_generated_members_with_actors(
        self,
        members: list[GeneratedMonsterORM],
        *,
        clan: GeneratedClan | None = None,
    ) -> list[GeneratedMonster]:
        if not members:
            return []
        documents = await self.actor_repo.fetch_actor_documents_by_keys([member.mongo_actor_key for member in members])
        result: list[GeneratedMonster] = []
        for member in members:
            document = documents.get(member.mongo_actor_key)
            if document is None:
                raise MissingGeneratedMonsterActorDocumentError(
                    f"Missing generated monster actor document: {member.mongo_actor_key}"
                )
            generated = _to_generated_monster(member, actor_document=document, clan=clan)
            result.append(generated)
        return result

    @staticmethod
    def _filter_clans(stmt, *, family_id: str | None, clan_id: uuid.UUID | str | None):
        if family_id:
            stmt = stmt.where(GeneratedClanORM.family_id == family_id)
        if clan_id:
            stmt = stmt.where(GeneratedClanORM.id == uuid.UUID(str(clan_id)))
        return stmt


def _to_generated_clan(clan: GeneratedClanORM) -> GeneratedClan:
    return GeneratedClan(
        id=clan.id,
        family_id=clan.family_id,
        identity_hash=clan.identity_hash,
        context_identity=dict(clan.context_identity or {}),
        context_hash=clan.context_hash,
        selected_traits=list(clan.selected_traits or []),
        title=clan.title,
        description=clan.description,
        encounter_texts=dict(clan.encounter_texts or {}),
        generation_version=int(clan.generation_version or 1),
        resource_version=str(clan.resource_version or "1"),
        metadata_=dict(clan.metadata_ or {}),
        context=dict(clan.context or {}),
        source_context=dict(clan.source_context or {}),
        lifecycle_status=str(clan.lifecycle_status or "active"),
        archived_at=clan.archived_at,
        expires_at=clan.expires_at,
        schema_version=int(clan.schema_version or 1),
        created_at=clan.created_at,
        updated_at=clan.updated_at,
    )


def _to_generated_monster(
    monster: GeneratedMonsterORM,
    *,
    actor_document: dict[str, Any],
    clan: GeneratedClan | None = None,
) -> GeneratedMonster:
    snapshots = actor_document.get("tier_snapshots") if isinstance(actor_document, dict) else {}
    active_snapshot = _first_tier_snapshot(snapshots)
    return GeneratedMonster(
        id=monster.id,
        clan_id=monster.clan_id,
        variant_id=monster.variant_id,
        member_hash=monster.member_hash,
        role=monster.role,
        title=monster.title,
        short_description=monster.short_description,
        min_tier=int(monster.min_tier),
        max_tier=int(monster.max_tier),
        mongo_actor_key=monster.mongo_actor_key,
        actor_document=dict(actor_document),
        active_snapshot=active_snapshot,
        metadata_=dict(monster.metadata_ or {}),
        context=dict(monster.context or {}),
        source_context=dict(monster.source_context or {}),
        lifecycle_status=str(monster.lifecycle_status or "active"),
        archived_at=monster.archived_at,
        expires_at=monster.expires_at,
        schema_version=int(monster.schema_version or 1),
        created_at=monster.created_at,
        updated_at=monster.updated_at,
        clan=clan,
    )


def _to_clan_orm(clan: GeneratedClan) -> GeneratedClanORM:
    return GeneratedClanORM(
        id=clan.id,
        family_id=clan.family_id,
        identity_hash=clan.identity_hash,
        context_identity=dict(clan.context_identity),
        context_hash=clan.context_hash,
        selected_traits=list(clan.selected_traits),
        title=clan.title,
        description=clan.description,
        encounter_texts=dict(clan.encounter_texts),
        generation_version=clan.generation_version,
        resource_version=str(clan.resource_version),
    )


def _to_monster_orm(monster: GeneratedMonster) -> GeneratedMonsterORM:
    return GeneratedMonsterORM(
        id=monster.id,
        clan_id=monster.clan_id,
        variant_id=monster.variant_id,
        member_hash=monster.member_hash,
        role=monster.role,
        title=monster.title,
        short_description=monster.short_description,
        min_tier=monster.min_tier,
        max_tier=monster.max_tier,
        mongo_actor_key=monster.mongo_actor_key,
    )


def _to_pool_entry(row: HabitatClanPoolEntryORM) -> HabitatClanPoolEntryDTO:
    return HabitatClanPoolEntryDTO.model_validate(
        {
            "scope_type": row.scope_type,
            "scope_id": row.scope_id,
            "clan_identity_hash": row.clan_identity_hash,
            "family_id": row.family_id,
            "pool_tier": row.pool_tier,
            "weight": row.weight,
            "enabled": row.enabled,
            "habitat": dict(row.habitat or {}),
            "policy_version": row.policy_version,
        }
    )


def _first_tier_snapshot(snapshots: Any) -> dict[str, Any]:
    if not isinstance(snapshots, dict) or not snapshots:
        return {}
    first_key = sorted(snapshots, key=_tier_sort_value)[0]
    snapshot = snapshots.get(first_key)
    return dict(snapshot) if isinstance(snapshot, dict) else {}


def _tier_sort_value(key: Any) -> int:
    raw = str(key).strip()
    if raw.startswith("tier_"):
        raw = raw.removeprefix("tier_")
    return int(raw)


__all__ = [
    "MonsterGenerationRepository",
    "_to_generated_clan",
    "_to_generated_monster",
    "_to_clan_orm",
    "_to_monster_orm",
]
