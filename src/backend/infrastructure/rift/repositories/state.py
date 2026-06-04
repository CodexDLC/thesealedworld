from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from src.backend.infrastructure.rift.models import RiftMembership, RiftNodePoolRecord, RiftSetting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RiftSettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, setting_key: str) -> RiftSetting | None:
        return await self.session.get(RiftSetting, setting_key)

    async def upsert(self, setting: RiftSetting) -> RiftSetting:
        merged = await self.session.merge(setting)
        await self.session.flush()
        return merged


class RiftNodePoolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, pool_node_id: str) -> RiftNodePoolRecord | None:
        return await self.session.get(RiftNodePoolRecord, pool_node_id)

    async def list_by_setting(self, setting_key: str) -> list[RiftNodePoolRecord]:
        result = await self.session.execute(
            select(RiftNodePoolRecord).where(RiftNodePoolRecord.setting_key == setting_key)
        )
        return list(result.scalars().all())

    async def upsert(self, node: RiftNodePoolRecord) -> RiftNodePoolRecord:
        merged = await self.session.merge(node)
        await self.session.flush()
        return merged


class RiftMembershipRepository:
    ACTIVE_RESTORE_STATUSES = {"active", "resumable"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, membership_id: int) -> RiftMembership | None:
        return await self.session.get(RiftMembership, membership_id)

    async def get_by_session(self, rift_session_id: str) -> RiftMembership | None:
        result = await self.session.execute(
            select(RiftMembership).where(RiftMembership.rift_session_id == str(rift_session_id))
        )
        return result.scalars().first()

    async def get_active_for_participant(self, participant_ref: str) -> RiftMembership | None:
        result = await self.session.execute(
            select(RiftMembership)
            .where(RiftMembership.participant_ref == str(participant_ref))
            .where(RiftMembership.status.in_(self.ACTIVE_RESTORE_STATUSES))
            .order_by(RiftMembership.updated_at.desc())
        )
        return result.scalars().first()

    async def list_by_instance(self, rift_instance_id: str) -> list[RiftMembership]:
        result = await self.session.execute(
            select(RiftMembership).where(RiftMembership.rift_instance_id == str(rift_instance_id))
        )
        return list(result.scalars().all())

    async def upsert(self, membership: RiftMembership) -> RiftMembership:
        merged = await self.session.merge(membership)
        await self.session.flush()
        return merged

    async def upsert_from_session_payload(
        self,
        payload: dict[str, Any],
        *,
        setting_key: str,
        source: str | None = None,
        source_ref: str | None = None,
        status: str | None = None,
    ) -> RiftMembership:
        existing = await self.get_by_session(str(payload["rift_session_id"]))
        values = {
            "rift_instance_id": str(payload["rift_instance_id"]),
            "rift_session_id": str(payload["rift_session_id"]),
            "participant_ref": str(payload.get("participant_ref") or payload.get("owner_id") or ""),
            "setting_key": setting_key,
            "status": status or str(payload.get("status") or "active"),
            "source": source,
            "source_ref": source_ref,
            "current_node_id": _optional_str(payload.get("current_node_id")),
            "previous_node_id": _optional_str(payload.get("previous_node_id")),
            "heading": _optional_str(payload.get("heading")),
            "active_encounter_id": _optional_str(payload.get("active_encounter_id")),
        }
        if existing is None:
            return await self.upsert(RiftMembership(**values))
        for key, value in values.items():
            setattr(existing, key, value)
        await self.session.flush()
        return existing

    async def update_snapshot_refs(
        self,
        *,
        rift_instance_id: str,
        mongo_snapshot_id: str,
        snapshot_version: int,
        participant_summaries: dict[str, dict[str, Any]],
    ) -> None:
        now = datetime.now(UTC)
        for membership in await self.list_by_instance(rift_instance_id):
            membership.mongo_snapshot_id = mongo_snapshot_id
            membership.snapshot_version = int(snapshot_version)
            summary = participant_summaries.get(membership.rift_session_id) or {}
            if "current_node_id" in summary:
                membership.current_node_id = _optional_str(summary.get("current_node_id"))
            if "active_encounter_id" in summary:
                membership.active_encounter_id = _optional_str(summary.get("active_encounter_id"))
            membership.updated_at = now
        await self.session.flush()

    async def mark_status(self, rift_session_id: str, *, status: str, completed: bool = False) -> RiftMembership | None:
        membership = await self.get_by_session(rift_session_id)
        if membership is None:
            return None
        membership.status = status
        if completed and membership.completed_at is None:
            membership.completed_at = datetime.now(UTC)
        await self.session.flush()
        return membership


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
