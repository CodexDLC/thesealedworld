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
    description: str
    text_content: dict[str, Any]
    scaled_attributes: dict[str, Any]
    scaled_skills: dict[str, Any]
    items: dict[str, Any]
    vitals: dict[str, Any]
    ai_profile: dict[str, Any]
    generation_meta: dict[str, Any]
    combat_actor_snapshot: dict[str, Any]
    metadata_: dict[str, Any]
    context: dict[str, Any]
    source_context: dict[str, Any]
    lifecycle_status: str
    archived_at: str
    expires_at: str
    schema_version: int
    created_at: str
    updated_at: str
    threat_rating: int
    gear_score: int | None
    visual: AdminMonsterVisual
    equipment: list[str] = field(default_factory=list)
    affixes: list[str] = field(default_factory=list)

    @property
    def equipment_items(self) -> list[dict[str, Any]]:
        return _equipment_items(self.items)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdminGeneratedMonsterMember:
        summary = dict(data.get("equipment_summary") or {})
        return cls(
            monster_id=str(data["monster_id"]),
            variant_key=str(data.get("variant_key") or ""),
            role=str(data.get("role") or ""),
            member_tier=int(data.get("member_tier") or 0),
            name_ru=str(data.get("name_ru") or ""),
            description=str(data.get("description") or ""),
            text_content=dict(data.get("text_content") or {}),
            scaled_attributes=dict(data.get("scaled_attributes") or {}),
            scaled_skills=dict(data.get("scaled_skills") or {}),
            items=dict(data.get("items") or {}),
            vitals=dict(data.get("vitals") or {}),
            ai_profile=dict(data.get("ai_profile") or {}),
            generation_meta=dict(data.get("generation_meta") or {}),
            combat_actor_snapshot=dict(data.get("combat_actor_snapshot") or {}),
            metadata_=dict(data.get("metadata_") or {}),
            context=dict(data.get("context") or {}),
            source_context=dict(data.get("source_context") or {}),
            lifecycle_status=str(data.get("lifecycle_status") or ""),
            archived_at=str(data.get("archived_at") or ""),
            expires_at=str(data.get("expires_at") or ""),
            schema_version=int(data.get("schema_version") or 1),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
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
    context_hash: str
    unique_hash: str
    raw_tags: dict[str, Any]
    flavor_content: dict[str, Any]
    name_ru: str
    description: str
    metadata_: dict[str, Any]
    context: dict[str, Any]
    source_context: dict[str, Any]
    lifecycle_status: str
    archived_at: str
    expires_at: str
    schema_version: int
    created_at: str
    updated_at: str
    visual: AdminMonsterVisual
    selected_traits: list[dict[str, Any]] = field(default_factory=list)
    members: list[AdminGeneratedMonsterMember] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdminGeneratedMonsterClan:
        return cls(
            clan_id=str(data["clan_id"]),
            family_id=str(data.get("family_id") or ""),
            tier=int(data.get("tier") or 0),
            zone_id=str(data.get("zone_id") or ""),
            context_hash=str(data.get("context_hash") or ""),
            unique_hash=str(data.get("unique_hash") or ""),
            raw_tags=dict(data.get("raw_tags") or {}),
            flavor_content=dict(data.get("flavor_content") or {}),
            name_ru=str(data.get("name_ru") or ""),
            description=str(data.get("description") or ""),
            metadata_=dict(data.get("metadata_") or {}),
            context=dict(data.get("context") or {}),
            source_context=dict(data.get("source_context") or {}),
            lifecycle_status=str(data.get("lifecycle_status") or ""),
            archived_at=str(data.get("archived_at") or ""),
            expires_at=str(data.get("expires_at") or ""),
            schema_version=int(data.get("schema_version") or 1),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            visual=AdminMonsterVisual.from_dict(data.get("visual")),
            selected_traits=[dict(item) for item in data.get("selected_traits") or [] if isinstance(item, dict)],
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

    async def regenerate_clan_family_images(self, clan_id: str) -> dict[str, Any]:
        return dict(
            await self._request("POST", f"/api/admin/monsters/generated/clans/{clan_id}/regenerate-family-images") or {}
        )

    async def regenerate_clan_images(self, clan_ids: list[str]) -> dict[str, Any]:
        return dict(
            await self._request(
                "POST",
                "/api/admin/monsters/generated/clans/regenerate-images",
                json={"clan_ids": clan_ids},
            )
            or {}
        )

    async def regenerate_member_image(self, member_id: str) -> dict[str, Any]:
        return dict(
            await self._request("POST", f"/api/admin/monsters/generated/members/{member_id}/regenerate-image") or {}
        )

    async def plan_generated_rebuild(
        self,
        *,
        family_id: str | None = None,
        clan_id: str | None = None,
        limit: int = 100,
        force: bool = False,
        remove_obsolete_members: bool = True,
    ) -> dict[str, Any]:
        return (
            await self._request(
                "POST",
                "/api/admin/monsters/generated/rebuild/plan",
                json=_rebuild_payload(
                    family_id=family_id,
                    clan_id=clan_id,
                    limit=limit,
                    force=force,
                    remove_obsolete_members=remove_obsolete_members,
                ),
            )
            or {}
        )

    async def apply_generated_rebuild(
        self,
        *,
        family_id: str | None = None,
        clan_id: str | None = None,
        limit: int = 100,
        force: bool = False,
        remove_obsolete_members: bool = True,
    ) -> dict[str, Any]:
        return (
            await self._request(
                "POST",
                "/api/admin/monsters/generated/rebuild/apply",
                json=_rebuild_payload(
                    family_id=family_id,
                    clan_id=clan_id,
                    limit=limit,
                    force=force,
                    remove_obsolete_members=remove_obsolete_members,
                ),
            )
            or {}
        )


def _rebuild_payload(
    *,
    family_id: str | None,
    clan_id: str | None,
    limit: int,
    force: bool,
    remove_obsolete_members: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "limit": limit,
        "force": force,
        "remove_obsolete_members": remove_obsolete_members,
    }
    if family_id:
        payload["family_id"] = family_id
    if clan_id:
        payload["clan_id"] = clan_id
    return payload


_SLOT_LABELS = {
    "amulet": "Амулет",
    "chest_armor": "Броня",
    "main_hand": "Правая рука",
    "off_hand": "Левая рука",
    "quiver": "Боезапас",
    "two_hand": "Две руки",
}

_SKILL_LABELS = {
    "skill_anatomy": "Анатомия",
    "skill_archery": "Стрельба",
    "skill_dual_wield": "Две руки",
    "skill_fencing": "Клинки/уколы",
    "skill_heavy_armor": "Тяжелая броня",
    "skill_light_armor": "Легкая броня",
    "skill_macing": "Ударное оружие",
    "skill_medium_armor": "Средняя броня",
    "skill_parrying": "Парирование",
    "skill_polearms": "Древковое оружие",
    "skill_ranged_combat": "Дальний бой",
    "skill_shield_mastery": "Щиты",
    "skill_swords": "Мечи",
    "skill_tactics": "Тактика",
    "skill_two_handed": "Двуручное оружие",
}

_BONUS_LABELS = {
    "anti_dodge_chance": "Пробитие уклонения",
    "bleed_damage_bonus": "Урон кровотечения",
    "bleed_resistance": "Сопротивление кровотечению",
    "control_resistance": "Сопротивление контролю",
    "damage_spread": "Разброс урона",
    "debuff_avoidance": "Защита от дебаффов",
    "environment_bio_resistance": "Био-защита",
    "environment_cold_resistance": "Защита от холода",
    "environment_gravity_resistance": "Гравитационная защита",
    "environment_heat_resistance": "Защита от жара",
    "evasion": "Уклонение",
    "evasion_penalty": "Штраф уклонения",
    "hp_regen": "Реген HP",
    "initiative": "Инициатива",
    "magical_resistance": "Магическая защита",
    "mental_resistance": "Ментальная защита",
    "physical_damage_bonus": "Физический урон",
    "physical_resistance": "Физическая защита",
    "poison_efficiency": "Эффективность яда",
    "poison_resistance": "Сопротивление яду",
    "quick_slot_capacity": "Быстрые слоты",
    "stamina_regen": "Реген выносливости",
}


def _equipment_items(items: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(items, dict):
        return []
    layout = dict(items.get("layout") or {})
    equipment = dict(layout.get("equipment") or {})
    by_id = dict(items.get("by_id") or {})
    rows: list[dict[str, Any]] = []
    for slot, item_id in sorted(equipment.items()):
        item = dict(by_id.get(str(item_id)) or {})
        combat = dict(item.get("combat") or {})
        generation = dict(item.get("generation") or {})
        rows.append(
            {
                "slot": str(slot),
                "slot_label": _SLOT_LABELS.get(str(slot), _humanize_key(slot)),
                "item_id": str(item_id),
                "name": str(item.get("name_ru") or item.get("name") or item.get("base_id") or item_id),
                "base_id": str(item.get("base_id") or item_id),
                "item_type": str(item.get("item_type") or item.get("kind") or item.get("item_kind") or ""),
                "power": _display_number(combat.get("power") or item.get("power")),
                "related_skill": _SKILL_LABELS.get(
                    str(combat.get("related_skill") or item.get("related_skill") or ""),
                    _humanize_key(combat.get("related_skill") or item.get("related_skill") or ""),
                ),
                "tags": [str(tag) for tag in combat.get("tags") or item.get("tags") or [] if tag],
                "bonuses": _bonus_rows(combat.get("bonuses") or item.get("bonuses") or {}),
                "implicit_bonuses": _bonus_rows(combat.get("implicit_bonuses") or item.get("implicit_bonuses") or {}),
                "affixes": _affix_rows(generation.get("affixes") or item.get("affixes") or []),
            }
        )
    return rows


def _affix_rows(raw_affixes: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_affixes, list):
        return []
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_affixes, start=1):
        affix = dict(raw) if isinstance(raw, dict) else {"id": str(raw)}
        name = affix.get("name_ru") or affix.get("name") or affix.get("id") or affix.get("affix_id") or f"affix {index}"
        rows.append(
            {
                "name": str(name),
                "bonuses": _bonus_rows(affix.get("bonuses") or affix.get("combat") or {}),
            }
        )
    return rows


def _bonus_rows(raw_bonuses: Any) -> list[dict[str, str]]:
    if not isinstance(raw_bonuses, dict):
        return []
    rows = []
    for key, value in sorted(raw_bonuses.items()):
        rows.append({"label": _BONUS_LABELS.get(str(key), _humanize_key(key)), "value": _display_bonus(value)})
    return rows


def _display_bonus(value: Any) -> str:
    try:
        number = float(str(value).replace("%", ""))
    except (TypeError, ValueError):
        return str(value)
    if abs(number) <= 1:
        return f"{number * 100:+.1f}%"
    return f"{number:+.1f}"


def _display_number(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def _humanize_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.replace("skill_", "").replace("_", " ").strip().capitalize()
