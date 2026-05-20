from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from src.backend.features.generation_ai.dto import AIGenerationTaskResultDTO, AIGenerationTaskSpecDTO
from src.backend.features.monsters.dto.ai import MonsterClanFlavorDTO
from src.backend.features.monsters.prompts import build_monster_clan_flavor_prompt
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import (
    DEFAULT_IMAGE_MODEL,
    build_clan_visual,
    build_member_visual,
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

        flavor_payload = generated.model_dump_with_variant_mapping()
        context_tags = list((clan.raw_tags or {}).get("tags") or [])
        member_roster = [
            {
                "variant_key": variant.variant_key,
                "role": family.variants[variant.variant_key].role if variant.variant_key in family.variants else "",
                "name": variant.name,
                "appearance": variant.appearance,
            }
            for variant in generated.variants_flavor
        ]
        flavor_payload["visual"] = build_clan_visual(
            family.id,
            clan_name=generated.name_ru,
            description=generated.description,
            context_tags=context_tags,
            member_roster=member_roster,
        )
        clan.flavor_content = flavor_payload
        clan.name_ru = generated.name_ru
        clan.description = generated.description
        flag_modified(clan, "flavor_content")

        for member in clan.members:
            variant = family.variants.get(member.variant_key)
            if variant is None:
                continue
            variant_flavor = generated.variants_by_key.get(member.variant_key)
            if variant_flavor is None:
                continue
            from src.backend.features.monsters.runtime.generation_fields import build_text_payload

            text_content = build_text_payload(variant, variant_flavor.model_dump(mode="json"))
            member.name_ru = text_content.name_ru
            member.description = text_content.appearance_ru
            member.text_content = text_content.model_dump(mode="json")
            generation_meta = dict(member.generation_meta or {})
            generation_meta["visual"] = build_member_visual(
                family.id,
                variant_key=member.variant_key,
                role=member.role,
                member_name=text_content.name_ru or member.variant_key,
                appearance=text_content.appearance_ru or variant.narrative_hint,
            )
            member.generation_meta = generation_meta
            flag_modified(member, "text_content")
            flag_modified(member, "generation_meta")

        await self.session.flush()
        return [
            build_monster_clan_image_task_spec_from_orm(clan),
            *(build_monster_member_image_task_spec_from_orm(member, clan=clan) for member in clan.members),
        ]


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

        flavor_content = dict(clan.flavor_content or {})
        visual = dict(flavor_content.get("visual") or {})
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
        flavor_content["visual"] = visual
        clan.flavor_content = flavor_content
        flag_modified(clan, "flavor_content")
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

        generation_meta = dict(member.generation_meta or {})
        visual = dict(generation_meta.get("visual") or {})
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
        generation_meta["visual"] = visual
        member.generation_meta = generation_meta
        flag_modified(member, "generation_meta")
        await self.session.flush()


def build_monster_clan_flavor_task_spec(clan: GeneratedClan) -> AIGenerationTaskSpecDTO:
    payload = build_monster_clan_flavor_payload(
        family_id=clan.family_id,
        tier=clan.tier,
        raw_tags=clan.raw_tags,
        variant_ids=sorted({member.variant_key for member in clan.members}),
    )
    return AIGenerationTaskSpecDTO(
        task_type=MONSTER_CLAN_FLAVOR_TASK,
        entity_type="monster_clan",
        entity_id=str(clan.id),
        output_kind="json",
        input_payload=payload,
        season_id=str((clan.raw_tags or {}).get("season_id") or ""),
        asset_hash=clan.unique_hash,
        priority=50,
        max_attempts=8,
        metadata={
            "family_id": clan.family_id,
            "zone_id": clan.zone_id,
            "unique_hash": clan.unique_hash,
        },
    )


def build_monster_clan_image_task_spec_from_orm(clan: GeneratedClanORM) -> AIGenerationTaskSpecDTO:
    visual = dict((clan.flavor_content or {}).get("visual") or {})
    asset_hash = str(visual.get("asset_hash") or clan.unique_hash)
    return AIGenerationTaskSpecDTO(
        task_type=MONSTER_CLAN_IMAGE_TASK,
        entity_type="monster_clan",
        entity_id=str(clan.id),
        output_kind="image",
        input_payload={
            "clan_id": str(clan.id),
            "family_id": clan.family_id,
            "name_ru": clan.name_ru,
            "description": clan.description,
            "visual": visual,
        },
        season_id=str((clan.raw_tags or {}).get("season_id") or ""),
        asset_hash=asset_hash,
        storage_prefix="monsters/generated/clans",
        priority=70,
        max_attempts=3,
        metadata={
            "family_id": clan.family_id,
            "zone_id": clan.zone_id,
            "unique_hash": clan.unique_hash,
            "visual_asset_hash": asset_hash,
        },
    )


def build_monster_member_image_task_spec_from_orm(
    member: GeneratedMonsterORM,
    *,
    clan: GeneratedClanORM | None = None,
) -> AIGenerationTaskSpecDTO:
    generation_meta = dict(member.generation_meta or {})
    visual = dict(generation_meta.get("visual") or {})
    asset_hash = str(visual.get("asset_hash") or member.id)
    family_id = clan.family_id if clan is not None else getattr(member.clan, "family_id", None)
    raw_tags = dict(clan.raw_tags or {}) if clan is not None else dict(getattr(member.clan, "raw_tags", None) or {})
    return AIGenerationTaskSpecDTO(
        task_type=MONSTER_MEMBER_IMAGE_TASK,
        entity_type="monster_member",
        entity_id=str(member.id),
        output_kind="image",
        input_payload={
            "member_id": str(member.id),
            "clan_id": str(member.clan_id),
            "family_id": family_id,
            "variant_key": member.variant_key,
            "role": member.role,
            "name_ru": member.name_ru,
            "description": member.description,
            "visual": visual,
        },
        season_id=str(raw_tags.get("season_id") or ""),
        asset_hash=asset_hash,
        storage_prefix="monsters/generated/members",
        priority=80,
        max_attempts=3,
        metadata={
            "family_id": family_id,
            "clan_id": str(member.clan_id),
            "variant_key": member.variant_key,
            "visual_asset_hash": asset_hash,
        },
    )


def build_monster_clan_flavor_payload(
    *,
    family_id: str,
    tier: int,
    raw_tags: dict[str, Any],
    variant_ids: list[str],
) -> dict[str, Any]:
    family = get_family_config(family_id)
    if family is None:
        raise ValueError(f"Unknown monster family: {family_id}")

    context_meta = dict(raw_tags.get("context_meta") or {})
    normalized_tags = list(raw_tags.get("tags") or [])
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
        "biome_id": raw_tags.get("biome_id") or "wasteland",
        "difficulty": raw_tags.get("difficulty") or "mid",
        "tier": tier,
        "rift_profile": context_meta.get("rift_profile"),
        "text_contract": {
            "clan": ["name_ru", "description", "loot_culture"],
            "member": ["name", "appearance", "detected", "ambush", "idle", "encounter", "behavior"],
            "encounter_states": {
                "detected": "player noticed the monster first",
                "ambush": "monster noticed or attacked first",
                "idle": "monster is observed before combat starts",
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
