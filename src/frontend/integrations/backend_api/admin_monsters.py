from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.frontend.core.api import BaseApiClient


@dataclass(frozen=True)
class AdminMonsterVisual:
    status: str = ""
    image_url: str = ""
    storage_key: str = ""
    storage_backend: str = ""
    pending_task_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> AdminMonsterVisual:
        payload = dict(data or {})
        return cls(
            status=str(payload.get("status") or ""),
            image_url=str(payload.get("image_url") or payload.get("generated_image_url") or ""),
            storage_key=str(payload.get("storage_key") or ""),
            storage_backend=str(payload.get("storage_backend") or ""),
            pending_task_id=str(payload.get("pending_task_id")) if payload.get("pending_task_id") else None,
        )


@dataclass(frozen=True)
class AdminGeneratedMonsterMember:
    monster_id: str
    variant_key: str
    role: str
    member_tier: int
    name_ru: str
    threat_rating: int
    gear_score: int | None
    visual: AdminMonsterVisual
    equipment: list[str] = field(default_factory=list)
    affixes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdminGeneratedMonsterMember:
        summary = dict(data.get("equipment_summary") or {})
        return cls(
            monster_id=str(data["monster_id"]),
            variant_key=str(data.get("variant_key") or ""),
            role=str(data.get("role") or ""),
            member_tier=int(data.get("member_tier") or 0),
            name_ru=str(data.get("name_ru") or ""),
            threat_rating=int(data.get("threat_rating") or 0),
            gear_score=int(data["gear_score"]) if data.get("gear_score") is not None else None,
            visual=AdminMonsterVisual.from_dict(data.get("visual")),
            equipment=[str(item) for item in summary.get("equipment") or []],
            affixes=[str(item) for item in summary.get("affixes") or []],
        )


@dataclass(frozen=True)
class AdminGeneratedMonsterClan:
    clan_id: str
    family_id: str
    tier: int
    zone_id: str
    name_ru: str
    description: str
    visual: AdminMonsterVisual
    members: list[AdminGeneratedMonsterMember] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdminGeneratedMonsterClan:
        return cls(
            clan_id=str(data["clan_id"]),
            family_id=str(data.get("family_id") or ""),
            tier=int(data.get("tier") or 0),
            zone_id=str(data.get("zone_id") or ""),
            name_ru=str(data.get("name_ru") or ""),
            description=str(data.get("description") or ""),
            visual=AdminMonsterVisual.from_dict(data.get("visual")),
            members=[AdminGeneratedMonsterMember.from_dict(row) for row in data.get("members") or []],
        )


class AdminMonstersApi(BaseApiClient):
    async def list_generated(
        self,
        *,
        family_id: str | None = None,
        role: str | None = None,
        missing_image: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AdminGeneratedMonsterClan]:
        params: dict[str, Any] = {"limit": limit, "offset": offset, "include_members": True}
        if family_id:
            params["family_id"] = family_id
        if role:
            params["role"] = role
        raw = await self._request("GET", "/api/admin/monsters/generated", params=params)
        items = list((raw or {}).get("items") or [])
        clans = [AdminGeneratedMonsterClan.from_dict(item) for item in items]
        if missing_image:
            clans = [
                clan
                for clan in clans
                if not clan.visual.image_url or any(not member.visual.image_url for member in clan.members)
            ]
        return clans

    async def get_generated_clan(self, clan_id: str) -> AdminGeneratedMonsterClan | None:
        raw = await self._request(
            "GET",
            "/api/admin/monsters/generated",
            params={"clan_id": clan_id, "include_members": True, "limit": 1},
        )
        items = list((raw or {}).get("items") or [])
        if not items:
            return None
        return AdminGeneratedMonsterClan.from_dict(items[0])

    async def regenerate_clan_image(self, clan_id: str) -> dict[str, Any]:
        return dict(
            await self._request("POST", f"/api/admin/monsters/generated/clans/{clan_id}/regenerate-image") or {}
        )

    async def regenerate_member_image(self, member_id: str) -> dict[str, Any]:
        return dict(
            await self._request("POST", f"/api/admin/monsters/generated/members/{member_id}/regenerate-image") or {}
        )
