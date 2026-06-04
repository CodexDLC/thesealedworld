from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO
from src.backend.features.monsters.prompts import build_monster_clan_flavor_prompt
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import (
    DEFAULT_IMAGE_MODEL,
    build_monster_visual_prompt,
)
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.generation_ai.registry import AIGenerationTaskRegistry
    from src.backend.features.monsters.dto.generation import GeneratedClan

MONSTER_CLAN_FLAVOR_TASK = "monster.clan_flavor"
MONSTER_CLAN_IMAGE_TASK = "monster.clan_image"
MONSTER_MEMBER_IMAGE_TASK = "monster.member_image"


class MonsterClanFlavorTaskHandler:
    task_type = MONSTER_CLAN_FLAVOR_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        return {
            "kind": "json",
            "prompt": build_monster_clan_flavor_prompt(dict(task.input_payload or {})),
            "schema": MonsterClanFlavorDTO,
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> list[AIGenerationTaskSpecDTO]:
        if self.session is None:
            raise RuntimeError("MonsterClanFlavorTaskHandler requires a database session to apply result")

        generated = MonsterClanFlavorDTO.model_validate(result.output_payload)

        clan_id = UUID(str(task.entity_id))
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.id == clan_id)
            .options(selectinload(GeneratedClanORM.members))
        )
        clan = await self.session.scalar(stmt)
        if clan is None:
            raise ValueError(f"Generated clan not found: {clan_id}")
        family = get_family_config(clan.family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {clan.family_id}")

        clan.title = generated.display_name.ru
        clan.description = generated.description.ru
        clan.encounter_texts = generated.encounter_texts.ru_dict()
        metadata = dict(clan.metadata_ or {})
        flavor_content = dict(metadata.get("flavor_content") or {})
        flavor_content["localized"] = {
            "display_name": generated.display_name.model_dump(mode="json"),
            "description": generated.description.model_dump(mode="json"),
            "visual_hint": generated.visual_hint.model_dump(mode="json"),
            "encounter_texts": generated.encounter_texts.model_dump(mode="json"),
        }
        flavor_content["loot_culture"] = generated.loot_culture.model_dump(mode="json")
        flavor_content["variants_flavor"] = {
            key: value
            for key, value in generated.model_dump_with_variant_mapping().get("variants_flavor", {}).items()
            if key
        }
        metadata["flavor_content"] = flavor_content
        clan.metadata_ = metadata

        for member in clan.members:
            variant = family.variants.get(member.variant_id)
            if variant is None:
                continue
            variant_flavor = generated.variants_by_key.get(member.variant_id)
            if variant_flavor is None:
                continue
            member.title = variant_flavor.display_name.ru
            member.short_description = variant_flavor.short_description.ru

        await self.session.flush()
        return []


class MonsterClanImageTaskHandler:
    task_type = MONSTER_CLAN_IMAGE_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        visual = dict((task.input_payload or {}).get("visual") or {})
        asset_payload = dict(visual.get("asset_payload") or {})
        storage_key = str(visual.get("storage_key") or "")
        if not storage_key:
            raise ValueError("Monster clan image task requires visual.storage_key")
        if not asset_payload:
            raise ValueError("Monster clan image task requires visual.asset_payload")

        return {
            "kind": "image",
            "prompt": build_monster_visual_prompt(asset_payload),
            "model": visual.get("image_model") or DEFAULT_IMAGE_MODEL,
            "content_type": "image/webp",
            "storage_key": storage_key,
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> None:
        if self.session is None:
            raise RuntimeError("MonsterClanImageTaskHandler requires a database session to apply result")

        clan_id = UUID(str(task.entity_id))
        clan = await self.session.scalar(select(GeneratedClanORM).where(GeneratedClanORM.id == clan_id))
        if clan is None:
            raise ValueError(f"Generated clan not found: {clan_id}")
        metadata = dict(clan.metadata_ or {})
        visual = dict(metadata.get("visual") or {})
        visual.update(
            {
                "status": "generated",
                "source": "ai_generated",
                "image_url": result.generated_url,
                "generated_image_url": result.generated_url,
                "storage_key": result.storage_key,
                "asset_hash": result.asset_hash or visual.get("asset_hash"),
                "storage_backend": result.storage_backend,
                "content_type": result.content_type,
                "size_bytes": result.size_bytes,
            }
        )
        metadata["visual"] = visual
        clan.metadata_ = metadata
        await self.session.flush()


class MonsterMemberImageTaskHandler:
    task_type = MONSTER_MEMBER_IMAGE_TASK

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def build_request(self, task: Any) -> dict[str, Any]:
        visual = dict((task.input_payload or {}).get("visual") or {})
        asset_payload = dict(visual.get("asset_payload") or {})
        storage_key = str(visual.get("storage_key") or "")
        if not storage_key:
            raise ValueError("Monster member image task requires visual.storage_key")
        if not asset_payload:
            raise ValueError("Monster member image task requires visual.asset_payload")

        return {
            "kind": "image",
            "prompt": build_monster_visual_prompt(asset_payload),
            "model": visual.get("image_model") or DEFAULT_IMAGE_MODEL,
            "content_type": "image/webp",
            "storage_key": storage_key,
        }

    async def apply_result(self, task: Any, result: AIGenerationTaskResultDTO) -> None:
        if self.session is None:
            raise RuntimeError("MonsterMemberImageTaskHandler requires a database session to apply result")

        member_id = UUID(str(task.entity_id))
        member = await self.session.scalar(select(GeneratedMonsterORM).where(GeneratedMonsterORM.id == member_id))
        if member is None:
            raise ValueError(f"Generated monster member not found: {member_id}")
        metadata = dict(member.metadata_ or {})
        visual = dict(metadata.get("visual") or {})
        visual.update(
            {
                "status": "generated",
                "source": "ai_generated",
                "image_url": result.generated_url,
                "generated_image_url": result.generated_url,
                "storage_key": result.storage_key,
                "asset_hash": result.asset_hash or visual.get("asset_hash"),
                "storage_backend": result.storage_backend,
                "content_type": result.content_type,
                "size_bytes": result.size_bytes,
            }
        )
        metadata["visual"] = visual
        member.metadata_ = metadata
        await self.session.flush()


def build_monster_clan_flavor_task_spec(clan: GeneratedClan) -> AIGenerationTaskSpecDTO:
    context_identity = dict(clan.context_identity or {})
    tier = int(context_identity.get("tier") or 0)
    payload = build_monster_clan_flavor_payload(
        family_id=clan.family_id,
        tier=tier,
        context_identity=context_identity,
        selected_traits=list(clan.selected_traits or []),
        variant_ids=sorted({member.variant_id for member in clan.members}),
    )
    return AIGenerationTaskSpecDTO(
        task_type=MONSTER_CLAN_FLAVOR_TASK,
        entity_type="monster_clan",
        entity_id=str(clan.id),
        output_kind="json",
        input_payload=payload,
        season_id=str(context_identity.get("season_id") or ""),
        asset_hash=clan.identity_hash,
        priority=50,
        max_attempts=8,
        metadata={
            "family_id": clan.family_id,
            "zone_id": context_identity.get("zone_id"),
            "identity_hash": clan.identity_hash,
        },
    )


def build_monster_clan_image_task_spec_from_orm(clan: GeneratedClanORM) -> AIGenerationTaskSpecDTO:
    visual = dict((clan.metadata_ or {}).get("visual") or {})
    asset_hash = str(visual.get("asset_hash") or clan.identity_hash)
    return AIGenerationTaskSpecDTO(
        task_type=MONSTER_CLAN_IMAGE_TASK,
        entity_type="monster_clan",
        entity_id=str(clan.id),
        output_kind="image",
        input_payload={
            "clan_id": str(clan.id),
            "family_id": clan.family_id,
            "name_ru": clan.title,
            "description": clan.description,
            "visual": visual,
        },
        season_id=str((clan.context_identity or {}).get("season_id") or ""),
        asset_hash=asset_hash,
        storage_prefix="monsters/generated/clans",
        priority=70,
        max_attempts=3,
        metadata={
            "family_id": clan.family_id,
            "zone_id": (clan.context_identity or {}).get("zone_id"),
            "identity_hash": clan.identity_hash,
            "visual_asset_hash": asset_hash,
        },
    )


def build_monster_member_image_task_spec_from_orm(
    member: GeneratedMonsterORM,
    *,
    clan: GeneratedClanORM | None = None,
) -> AIGenerationTaskSpecDTO:
    metadata = dict(member.metadata_ or {})
    visual = dict(metadata.get("visual") or {})
    asset_hash = str(visual.get("asset_hash") or member.id)
    family_id = clan.family_id if clan is not None else getattr(member.clan, "family_id", None)
    context_identity = (
        dict(clan.context_identity or {})
        if clan is not None
        else dict(getattr(member.clan, "context_identity", None) or {})
    )
    return AIGenerationTaskSpecDTO(
        task_type=MONSTER_MEMBER_IMAGE_TASK,
        entity_type="monster_member",
        entity_id=str(member.id),
        output_kind="image",
        input_payload={
            "member_id": str(member.id),
            "clan_id": str(member.clan_id),
            "family_id": family_id,
            "variant_id": member.variant_id,
            "role": member.role,
            "name_ru": member.title,
            "description": member.short_description,
            "visual": visual,
        },
        season_id=str(context_identity.get("season_id") or ""),
        asset_hash=asset_hash,
        storage_prefix="monsters/generated/members",
        priority=80,
        max_attempts=3,
        metadata={
            "family_id": family_id,
            "clan_id": str(member.clan_id),
            "variant_id": member.variant_id,
            "visual_asset_hash": asset_hash,
        },
    )


def build_monster_clan_flavor_payload(
    *,
    family_id: str,
    tier: int,
    context_identity: dict[str, Any] | None = None,
    selected_traits: list[dict[str, Any]] | None = None,
    variant_ids: list[str],
) -> dict[str, Any]:
    family = get_family_config(family_id)
    if family is None:
        raise ValueError(f"Unknown monster family: {family_id}")

    context_identity = dict(context_identity or {})
    selected_traits = list(selected_traits or context_identity.get("selected_traits") or [])
    context_meta = dict(context_identity.get("context_meta") or {})
    normalized_tags = list(context_identity.get("tags") or [])
    units_with_roles = {
        variant_id: f"[{family.variants[variant_id].role.title()}] {family.variants[variant_id].narrative_hint}"
        for variant_id in variant_ids
        if variant_id in family.variants
    }
    return {
        "family_id": family.id,
        "archetype": family.archetype,
        "organization": family.organization_type,
        "family_tags": family.default_tags,
        "context_tags": normalized_tags,
        "biome_id": context_identity.get("biome_id") or "wasteland",
        "difficulty": context_identity.get("difficulty") or "mid",
        "tier": tier,
        "rift_profile": context_meta.get("rift_profile"),
        "selected_traits": selected_traits,
        "text_contract": {
            "locales": ["ru", "en"],
            "clan": ["display_name", "description", "visual_hint", "encounter_texts", "loot_culture"],
            "member": ["variant_id", "display_name", "short_description", "appearance", "visual_hint"],
            "encounter_states": {
                "patrol": "moving or travel patrol contact",
                "ambush": "surprise or monster-initiated attack",
                "lair": "guarded node, boss, heart guard, or lair-like position",
                "random_meeting": "ordinary random node meeting",
            },
        },
        "units_to_name": units_with_roles,
        "loot_culture_contract": {
            "purpose": "Generate family-level equipment culture for future item names, descriptions, and images.",
            "must_reflect": [
                "family archetype and organization",
                "location, biome, context tags, and rift profile",
                "how this concrete clan obtains, repairs, carries, or repurposes gear",
                "what materials and objects should appear on this clan's weapons, shields, armor, garments, and trophies",
            ],
            "do_not": [
                "do not return generic fantasy gear culture",
                "do not describe a single individual monster",
                "do not make loot_culture a drop table or mechanical loot profile",
            ],
        },
    }


def register_generation_ai_tasks(registry: AIGenerationTaskRegistry, *, session: AsyncSession | None = None) -> None:
    registry.register(MonsterClanFlavorTaskHandler(session=session))
    registry.register(MonsterClanImageTaskHandler(session=session))
    registry.register(MonsterMemberImageTaskHandler(session=session))
