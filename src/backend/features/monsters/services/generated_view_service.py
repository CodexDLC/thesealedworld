from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto.generated_view import (
    GeneratedMonsterEquipmentSummaryDTO,
    GeneratedMonstersResponseDTO,
)
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster
    from src.backend.features.monsters.repositories import MonsterGenerationRepository


class GeneratedMonsterViewService:
    def __init__(self, repository: MonsterGenerationRepository) -> None:
        self.repository = repository
        self.gear_score_service = MonsterGearScoreService()

    async def list_generated(
        self,
        *,
        family_id: str | None = None,
        clan_id: str | None = None,
        role: str | None = None,
        include_members: bool = True,
        limit: int = 25,
        offset: int = 0,
    ) -> GeneratedMonstersResponseDTO:
        total = await self.repository.count_generated_clans(family_id=family_id, clan_id=clan_id)
        clans = await self.repository.list_generated_clans_page(
            family_id=family_id,
            clan_id=clan_id,
            limit=limit,
            offset=offset,
        )
        clans = await self._refresh_stale_clans(clans)
        return GeneratedMonstersResponseDTO(
            items=[self._clan_payload(clan, role=role, include_members=include_members) for clan in clans],
            pagination={
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + limit < total,
            },
        )

    async def _refresh_stale_clans(self, clans: list[GeneratedClan]) -> list[GeneratedClan]:
        return clans

    def _needs_gear_score_refresh(self, clan: GeneratedClan) -> bool:
        del clan
        return False

    def _clan_payload(self, clan: GeneratedClan, *, role: str | None, include_members: bool) -> dict[str, Any]:
        members = [member for member in clan.members if role is None or member.role == role]
        summary = self._summary(clan, members, role=role)
        context_identity = dict(clan.context_identity or {})
        flavor_content = _flavor_content(clan, visual=_visual((clan.metadata_ or {}).get("visual")))
        localized = _clan_localized(clan, flavor_content=flavor_content)
        return {
            "clan_id": str(clan.id),
            "family_id": clan.family_id,
            "tier": _optional_int(context_identity.get("tier")) or 0,
            "zone_id": clan.zone_id,
            "context_hash": clan.context_hash,
            "identity_hash": clan.identity_hash,
            "unique_hash": clan.unique_hash,
            "context_identity": context_identity,
            "selected_traits": list(clan.selected_traits or []),
            "title": clan.title,
            "name_ru": clan.title,
            "localized": localized,
            "description": clan.description,
            "encounter_texts": dict(clan.encounter_texts or {}),
            "raw_tags": _raw_tags(clan, context_identity=context_identity, gear_summary=summary),
            "flavor_content": flavor_content,
            "generation_version": clan.generation_version,
            "resource_version": clan.resource_version,
            "metadata_": dict(clan.metadata_ or {}),
            "context": dict(clan.context or {}),
            "source_context": dict(clan.source_context or {}),
            "lifecycle_status": clan.lifecycle_status,
            "archived_at": clan.archived_at,
            "expires_at": clan.expires_at,
            "schema_version": clan.schema_version,
            "created_at": clan.created_at,
            "updated_at": clan.updated_at,
            "visual": _visual((clan.metadata_ or {}).get("visual")),
            "gear_score_summary": summary,
            "members": [self._member_payload(member, clan=clan) for member in self._sort_members(members)]
            if include_members
            else [],
        }

    def _summary(self, clan: GeneratedClan, members: list[GeneratedMonster], *, role: str | None) -> dict[str, Any]:
        del clan, role
        return self.gear_score_service.build_clan_summary(members)

    @staticmethod
    def _member_payload(member: GeneratedMonster, *, clan: GeneratedClan) -> dict[str, Any]:
        snapshot = dict(member.active_snapshot or {})
        text_content = _dict(snapshot.get("text_content"))
        variant_flavor = _variant_flavor(clan, member.variant_id)
        display_text_content = _member_text_content(
            text_content,
            title=member.title,
            short_description=member.short_description,
            variant_flavor=variant_flavor,
        )
        items = _dict(snapshot.get("items"))
        gear_score = _optional_int(snapshot.get("gear_score"))
        name = member.title or str(text_content.get("name_ru") or "")
        description = member.short_description or str(text_content.get("description_ru") or "")
        return {
            "member_id": str(member.id),
            "monster_id": str(member.id),
            "clan_id": str(member.clan_id),
            "variant_id": member.variant_id,
            "variant_key": member.variant_id,
            "member_hash": member.member_hash,
            "role": member.role,
            "title": member.title,
            "name_ru": name,
            "localized": _member_localized(
                title=member.title,
                variant_id=member.variant_id,
                short_description=member.short_description,
                variant_flavor=variant_flavor,
            ),
            "short_description": member.short_description or "",
            "description": description,
            "min_tier": member.min_tier,
            "max_tier": member.max_tier,
            "member_tier": _optional_int(snapshot.get("member_tier"))
            or _optional_int(snapshot.get("effective_tier"))
            or 0,
            "mongo_actor_key": member.mongo_actor_key,
            "text_content": display_text_content,
            "scaled_attributes": _dict(snapshot.get("scaled_attributes") or snapshot.get("attributes")),
            "scaled_skills": _dict(snapshot.get("scaled_skills") or snapshot.get("skills")),
            "items": items,
            "vitals": _dict(snapshot.get("vitals") or snapshot.get("status")),
            "ai_profile": _dict(snapshot.get("ai_profile")),
            "generation_meta": _generation_meta(snapshot),
            "combat_actor_snapshot": _dict(snapshot.get("combat_snapshot_input")),
            "metadata_": dict(member.metadata_ or {}),
            "context": dict(member.context or {}),
            "source_context": dict(member.source_context or {}),
            "lifecycle_status": member.lifecycle_status,
            "archived_at": member.archived_at,
            "expires_at": member.expires_at,
            "schema_version": member.schema_version,
            "created_at": member.created_at,
            "updated_at": member.updated_at,
            "threat_rating": gear_score or 0,
            "gear_score": gear_score,
            "visual": _visual((member.metadata_ or {}).get("visual")),
            "equipment_summary": _equipment_summary(items),
        }

    @staticmethod
    def _sort_members(members: list[GeneratedMonster]) -> list[GeneratedMonster]:
        return sorted(
            members,
            key=lambda member: (
                _optional_int(_balance(member).get("gear_score")) is None,
                _optional_int(_balance(member).get("gear_score")) or 0,
                member.role,
                member.variant_id,
            ),
        )


def _balance(member: GeneratedMonster) -> dict[str, Any]:
    gear_score = member.active_snapshot.get("gear_score")
    return {"gear_score": gear_score} if gear_score is not None else {}


def _raw_tags(clan: GeneratedClan, *, context_identity: dict[str, Any], gear_summary: dict[str, Any]) -> dict[str, Any]:
    habitat = _dict(context_identity.get("habitat"))
    raw = dict(context_identity)
    if habitat:
        raw["biome"] = habitat.get("biome")
        raw["habitat_keys"] = habitat.get("keys") or []
    raw["biome_id"] = context_identity.get("biome_id") or raw.get("biome")
    raw["selected_traits"] = list(clan.selected_traits or [])
    raw["gear_score_summary"] = dict(gear_summary)
    return raw


def _flavor_content(clan: GeneratedClan, *, visual: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(clan.metadata_ or {})
    content = _dict(metadata.get("flavor_content"))
    content.setdefault("visual", visual)
    content["encounter_texts"] = dict(clan.encounter_texts or {})
    return content


def _variant_flavor(clan: GeneratedClan, variant_id: str) -> dict[str, Any]:
    metadata = dict(clan.metadata_ or {})
    flavor_content = _dict(metadata.get("flavor_content"))
    variants = _dict(flavor_content.get("variants_flavor"))
    return _dict(variants.get(variant_id))


def _clan_localized(clan: GeneratedClan, *, flavor_content: dict[str, Any]) -> dict[str, Any]:
    localized = _dict(flavor_content.get("localized"))
    localized.setdefault("display_name", {"ru": clan.title, "en": clan.title})
    localized.setdefault("description", {"ru": clan.description, "en": clan.description})
    localized.setdefault("visual_hint", localized.get("description", {"ru": clan.description, "en": clan.description}))
    encounter_texts = _dict(localized.get("encounter_texts"))
    if not encounter_texts:
        encounter_texts = {
            key: {"ru": str(value), "en": str(value)} for key, value in dict(clan.encounter_texts or {}).items()
        }
    localized["encounter_texts"] = encounter_texts
    return localized


def _member_localized(
    *,
    title: str,
    variant_id: str,
    short_description: str,
    variant_flavor: dict[str, Any],
) -> dict[str, Any]:
    display_name = _localized_text(variant_flavor.get("display_name"), fallback=title or variant_id)
    localized_short_description = _localized_text(
        variant_flavor.get("short_description"),
        fallback=short_description or "",
    )
    appearance = _localized_text(variant_flavor.get("appearance"), fallback=short_description or "")
    visual_hint = _localized_text(
        variant_flavor.get("visual_hint"),
        fallback=str(variant_flavor.get("visual_hint_ru") or short_description or ""),
    )
    return {
        "display_name": display_name,
        "short_description": localized_short_description,
        "appearance": appearance,
        "visual_hint": visual_hint,
    }


def _localized_text(value: Any, *, fallback: str) -> dict[str, str]:
    if isinstance(value, dict):
        ru = str(value.get("ru") or fallback)
        en = str(value.get("en") or ru)
        return {"ru": ru, "en": en}
    text = str(value or fallback)
    return {"ru": text, "en": text}


def _member_text_content(
    text_content: dict[str, Any],
    *,
    title: str,
    short_description: str,
    variant_flavor: dict[str, Any],
) -> dict[str, Any]:
    content = dict(text_content)
    if title:
        content["name_ru"] = title
        content["short_name_ru"] = title
    if short_description:
        content["description_ru"] = short_description
    visual_hint = _localized_text(
        variant_flavor.get("visual_hint"), fallback=str(variant_flavor.get("visual_hint_ru") or "")
    )
    localized = _member_localized(
        title=title,
        variant_id="",
        short_description=short_description,
        variant_flavor=variant_flavor,
    )
    content["localized"] = localized
    content["appearance_ru"] = localized["appearance"]["ru"]
    if visual_hint:
        content["visual_hint"] = visual_hint["ru"]
    return content


def _generation_meta(snapshot: dict[str, Any]) -> dict[str, Any]:
    balance = _dict(snapshot.get("balance"))
    for key in ("raw_gear_score", "gear_score", "assembly_cost", "gear_score_version"):
        if key in snapshot:
            balance[key] = snapshot[key]
    return {
        "balance": balance,
        "meta": _dict(snapshot.get("meta")),
        "snapshot_tier": snapshot.get("snapshot_tier"),
        "effective_tier": snapshot.get("effective_tier"),
    }


def _equipment_summary(items: dict[str, Any]) -> GeneratedMonsterEquipmentSummaryDTO:
    layout = _dict(items.get("layout"))
    equipment = _dict(layout.get("equipment"))
    by_id = _dict(items.get("by_id"))
    rows: list[str] = []
    weapons: list[str] = []
    armor: list[str] = []
    affixes: list[str] = []
    for slot, item_id in sorted(equipment.items()):
        item = _dict(by_id.get(str(item_id)))
        label = str(item.get("name_ru") or item.get("name") or item.get("base_id") or item_id)
        row = f"{slot}: {label}"
        rows.append(row)
        kind = str(item.get("kind") or item.get("item_type") or item.get("item_kind") or "").lower()
        if kind in {"weapon", "shield", "ammo"} or slot in {"main_hand", "off_hand", "two_hand", "quiver"}:
            weapons.append(row)
        elif kind in {"armor", "accessory"} or slot not in {"main_hand", "off_hand", "two_hand", "quiver"}:
            armor.append(row)
        affixes.extend(_affix_labels(item.get("affixes")))
        generation = _dict(item.get("generation"))
        affixes.extend(_affix_labels(generation.get("affixes")))
    return GeneratedMonsterEquipmentSummaryDTO(
        equipment=rows,
        weapons=weapons,
        armor=armor,
        affixes=sorted({affix for affix in affixes if affix}),
    )


def _affix_labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for index, raw in enumerate(value, start=1):
        if isinstance(raw, dict):
            labels.append(str(raw.get("name_ru") or raw.get("name") or raw.get("id") or raw.get("affix_id") or ""))
        elif raw:
            labels.append(str(raw))
        else:
            labels.append(f"affix {index}")
    return labels


def _visual(value: Any) -> dict[str, Any]:
    visual = dict(value) if isinstance(value, dict) else {}
    return {
        "status": str(visual.get("status") or ""),
        "source": str(visual.get("source") or ""),
        "image_url": str(visual.get("image_url") or ""),
        "generated_image_url": str(visual.get("generated_image_url") or ""),
        "placeholder_image_url": str(visual.get("placeholder_image_url") or ""),
        "storage_key": str(visual.get("storage_key") or ""),
        "storage_backend": str(visual.get("storage_backend") or ""),
        "asset_hash": str(visual.get("asset_hash") or ""),
        "content_type": str(visual.get("content_type") or ""),
        "size_bytes": _optional_int(visual.get("size_bytes")),
        "pending_task_id": str(visual.get("pending_task_id")) if visual.get("pending_task_id") else None,
    }


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = ["GeneratedMonsterViewService"]
