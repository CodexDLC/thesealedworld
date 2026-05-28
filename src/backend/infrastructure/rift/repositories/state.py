from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from src.backend.infrastructure.rift.models import (
    RiftInstanceState,
    RiftNodePoolRecord,
    RiftPortalKey,
    RiftRunState,
    RiftSetting,
)

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


class RiftInstanceStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, rift_instance_id: str) -> RiftInstanceState | None:
        return await self.session.get(RiftInstanceState, rift_instance_id)

    async def upsert(self, state: RiftInstanceState) -> RiftInstanceState:
        merged = await self.session.merge(state)
        await self.session.flush()
        return merged


class RiftRunStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, rift_run_id: str) -> RiftRunState | None:
        return await self.session.get(RiftRunState, rift_run_id)

    async def list_by_instance(self, rift_instance_id: str) -> list[RiftRunState]:
        result = await self.session.execute(
            select(RiftRunState).where(RiftRunState.rift_instance_id == rift_instance_id)
        )
        return list(result.scalars().all())

    async def upsert(self, state: RiftRunState) -> RiftRunState:
        merged = await self.session.merge(state)
        await self.session.flush()
        return merged


class RiftPortalKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, portal_id: str) -> RiftPortalKey | None:
        return await self.session.get(RiftPortalKey, portal_id)

    async def get_by_rift_session(self, rift_session_id: str) -> RiftPortalKey | None:
        result = await self.session.execute(
            select(RiftPortalKey).where(RiftPortalKey.rift_session_id == rift_session_id)
        )
        return result.scalars().first()

    async def list_by_status(self, statuses: list[str]) -> list[RiftPortalKey]:
        result = await self.session.execute(select(RiftPortalKey).where(RiftPortalKey.status.in_(statuses)))
        return list(result.scalars().all())

    async def upsert(self, portal: RiftPortalKey) -> RiftPortalKey:
        merged = await self.session.merge(portal)
        await self.session.flush()
        return merged

    async def upsert_from_payload(self, payload: dict[str, Any]) -> RiftPortalKey:
        return await self.upsert(_portal_from_payload(payload))

    async def mark_status(
        self,
        portal_id: str,
        *,
        status: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> RiftPortalKey | None:
        portal = await self.get(portal_id)
        if portal is None:
            return None
        portal.status = status
        state_json = dict(portal.state_json or {})
        if reason:
            state_json["status_reason"] = reason
        if details:
            state_json["details"] = {**dict(state_json.get("details") or {}), **details}
        portal.state_json = state_json
        if status in {"completed", "failed_sealed", "abandoned", "expired"} and portal.closed_at is None:
            portal.closed_at = datetime.now(UTC)
        if status == "archived" and portal.archived_at is None:
            portal.archived_at = datetime.now(UTC)
        await self.session.flush()
        return portal


def _portal_from_payload(payload: dict[str, Any]) -> RiftPortalKey:
    exit_policy = dict(payload.get("exit_policy") or {})
    return RiftPortalKey(
        portal_id=str(payload["portal_id"]),
        portal_key=str(payload.get("portal_key") or payload["portal_id"]),
        status=str(payload.get("status") or "active"),
        source=str(payload.get("source") or "unknown"),
        source_ref=_optional_str(payload.get("source_ref")),
        rift_key=_optional_str(payload.get("rift_key")),
        entry_reason=_optional_str(payload.get("entry_reason")),
        entry_mode=str(payload.get("entry_mode") or "direct"),
        owner_type=str(payload.get("owner_type") or "character"),
        owner_id=str(payload.get("owner_id") or ""),
        participant_scope=str(payload.get("participant_scope") or "solo"),
        rift_session_id=_optional_str(payload.get("rift_session_id")),
        rift_instance_id=_optional_str(payload.get("rift_instance_id")),
        service_id=_optional_str(payload.get("service_id")),
        source_location_id=_optional_str(payload.get("source_location_id")),
        exit_target_state=_optional_str(exit_policy.get("target_state") or payload.get("exit_target_state")),
        exit_location_id=_optional_str(exit_policy.get("location_id") or payload.get("exit_location_id")),
        expires_at=_datetime_from_epoch(payload.get("expires_at")),
        closed_at=_datetime_from_epoch(payload.get("closed_at")),
        archived_at=_datetime_from_epoch(payload.get("archived_at")),
        entry_context_json=dict(payload.get("entry_context") or {}),
        exit_policy_json=exit_policy,
        runtime_refs_json={
            "rift_session_id": _optional_str(payload.get("rift_session_id")),
            "rift_instance_id": _optional_str(payload.get("rift_instance_id")),
        },
        state_json={
            "status_reason": _optional_str(payload.get("status_reason")),
            "details": dict(payload.get("details") or {}),
        },
        metadata_=dict(payload.get("metadata") or {}),
        context=dict(payload.get("context") or {}),
        source_context=dict(payload.get("source_context") or {}),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _datetime_from_epoch(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except (TypeError, ValueError, OSError):
        return None
