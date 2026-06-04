from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from src.backend.infrastructure.monsters import GeneratedClanORM

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import ItemGenerationRequestDTO


class ItemMonsterNarrativeIntegration:
    """Item text facade for generated monster clan narrative stored in the DB."""

    def __init__(self, session: Any) -> None:
        self.session = session

    async def enrich_request_from_db_clan(self, request: ItemGenerationRequestDTO) -> ItemGenerationRequestDTO:
        source_context = dict(request.source_context or {})
        owner_family = source_context.get("owner_family")
        clan_id = source_context.get("clan_id")
        if clan_id is None and isinstance(owner_family, dict):
            clan_id = owner_family.get("clan_id")
        if clan_id is None:
            return request

        source_context["clan_id"] = str(clan_id)
        source_context["owner_family"] = await self._load_owner_family(str(clan_id))
        return request.model_copy(update={"source_context": source_context})

    async def _load_owner_family(self, clan_id: str) -> dict[str, Any]:
        try:
            clan_uuid = UUID(str(clan_id))
        except ValueError as exc:
            raise ValueError(f"Invalid generated clan id for item text: {clan_id}") from exc

        clan = await self.session.scalar(select(GeneratedClanORM).where(GeneratedClanORM.id == clan_uuid))
        if clan is None:
            raise ValueError(f"Generated clan not found for item text: {clan_id}")

        metadata = dict(clan.metadata_ or {})
        flavor_content = _dict(metadata.get("flavor_content"))
        context_identity = _dict(clan.context_identity)
        habitat = _dict(context_identity.get("habitat"))
        return {
            "clan_id": str(clan.id),
            "family_resource_id": clan.family_id,
            "clan_name_ru": clan.title or "",
            "clan_description": clan.description or "",
            "biome_id": str(context_identity.get("biome_id") or habitat.get("biome") or ""),
            "difficulty": str(context_identity.get("difficulty") or ""),
            "tags": _strings(context_identity.get("tags")),
            "habitat_keys": _strings(habitat.get("keys")),
            "encounter_texts": dict(clan.encounter_texts or {}),
            "loot_culture": dict(flavor_content.get("loot_culture") or {}),
        }


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]
