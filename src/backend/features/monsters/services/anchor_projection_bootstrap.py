from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.schemas.session import CharacterSessionAttributesDTO
from src.backend.features.monsters.dto.generation import GeneratedMonster
from src.backend.features.monsters.integrations.item_generation import (
    build_monster_item_request,
    to_item_generation_requests,
)
from src.backend.features.monsters.resources import get_family_config
from src.backend.features.monsters.resources.visuals import build_member_visual
from src.backend.features.monsters.runtime.combat_actor_input import MonsterCombatActorInputBuilder
from src.backend.features.monsters.runtime.generation_fields import (
    build_generated_monster_template,
    build_member_tier,
)
from src.backend.features.monsters.services.gear_score_service import MonsterGearScoreService
from src.backend.infrastructure.monsters.managers import (
    AnchorProjectionSnapshotCacheManager,
)

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
    from src.backend.features.monsters.dto.resources import MonsterFamilyDTO, MonsterVariantDTO


ANCHOR_PROJECTION_FAMILY_ID = "anchor_sovereigns"
ANCHOR_PROJECTION_ZONE_ID = "system:anchor_projections"
ANCHOR_PROJECTION_CONTEXT_HASH = "system:anchor_projections:v1"
ANCHOR_PROJECTION_UNIQUE_HASH = "system:anchor_projections:anchor_sovereigns:v1"
ANCHOR_PROJECTION_NAMES_RU: dict[str, str] = {
    "north_stasis_sovereign": "Проекция Северного Стазиса",
    "south_entropy_sovereign": "Проекция Южной Энтропии",
    "west_gravity_sovereign": "Проекция Западной Гравитации",
    "east_evolution_sovereign": "Проекция Восточной Эволюции",
}


class AnchorProjectionBootstrapService:
    """Builds Redis-cached combat pre-actors for anchor chaos interventions."""

    def __init__(
        self,
        *,
        item_generation: Any,
        redis: Any | None = None,
        actor_builder: MonsterCombatActorInputBuilder | None = None,
    ) -> None:
        self.item_generation = item_generation
        self.redis = redis
        self.actor_builder = actor_builder or MonsterCombatActorInputBuilder()

    async def bootstrap(self) -> dict[str, Any]:
        family = get_family_config(ANCHOR_PROJECTION_FAMILY_ID)
        if family is None:
            raise ValueError(f"Anchor projection family is missing: {ANCHOR_PROJECTION_FAMILY_ID}")

        members = await self._build_members(family)
        snapshots = {member.variant_key: self.actor_builder.build_snapshot(member) for member in members}
        if self.redis is not None:
            await AnchorProjectionSnapshotCacheManager(self.redis).save_snapshots(snapshots)
            logger.bind(variants=sorted(snapshots)).info("AnchorProjectionSnapshotsCached")

        return {
            "family_id": family.id,
            "clan_id": str(uuid.uuid5(uuid.NAMESPACE_URL, ANCHOR_PROJECTION_UNIQUE_HASH)),
            "members": sorted(snapshots),
            "redis_cached": self.redis is not None,
        }

    async def _build_members(self, family: MonsterFamilyDTO) -> list[GeneratedMonster]:
        variants = [family.variants[variant_id] for variant_id in family.hierarchy.boss]
        runtime_items = await self._build_runtime_items(family, variants)
        clan_id = uuid.uuid5(uuid.NAMESPACE_URL, ANCHOR_PROJECTION_UNIQUE_HASH)
        members: list[GeneratedMonster] = []
        for variant in variants:
            member_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{ANCHOR_PROJECTION_UNIQUE_HASH}:{variant.id}")
            template = build_generated_monster_template(
                family,
                variant,
                context_tier=7,
                owner_key=variant.id,
                runtime_items=runtime_items,
                generated_text={
                    "name_ru": ANCHOR_PROJECTION_NAMES_RU.get(variant.id, variant.id),
                    "short_name_ru": ANCHOR_PROJECTION_NAMES_RU.get(variant.id, variant.id),
                    "appearance_ru": variant.narrative_hint,
                },
                source={
                    "bootstrap": "anchor_projection",
                    "family_id": family.id,
                    "variant_id": variant.id,
                },
            )
            vitals = CharacterVitalsCalculator.build_initial_vitals(
                CharacterSessionAttributesDTO.model_validate(template.scaled_attributes.model_dump(mode="json")),
                profile_key=f"monster:{family.archetype}",
            ).model_dump(mode="json")
            member = GeneratedMonster(
                id=member_id,
                clan_id=clan_id,
                variant_key=variant.id,
                role=variant.role,
                member_tier=template.member_tier,
                threat_rating=0,
                name_ru=template.text_content.name_ru or ANCHOR_PROJECTION_NAMES_RU.get(variant.id, variant.id),
                description=template.text_content.appearance_ru or variant.narrative_hint,
                text_content=template.text_content.model_dump(mode="json"),
                scaled_attributes=template.scaled_attributes.model_dump(mode="json"),
                scaled_skills=template.scaled_skills.model_dump(mode="json")["skills"],
                items=template.items.model_dump(mode="json"),
                vitals=vitals,
                ai_profile=template.ai_profile.model_dump(mode="json"),
                generation_meta={
                    "schema_version": 1,
                    "source": "anchor_projection_bootstrap",
                    "meta": template.meta.model_dump(mode="json"),
                    "balance": template.balance.model_dump(mode="json"),
                    "family_modifiers": template.family_modifiers,
                    "visual": build_member_visual(
                        family.id,
                        variant_key=variant.id,
                        role=variant.role,
                        member_name=template.text_content.name_ru or variant.id,
                        appearance=variant.narrative_hint,
                    ),
                },
            )
            MonsterGearScoreService(self.actor_builder).apply_monster_gear_score(member)
            members.append(member)
        return members

    async def _build_runtime_items(
        self, family: MonsterFamilyDTO, variants: list[MonsterVariantDTO]
    ) -> list[RuntimeItemProjectionDTO]:
        from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS

        requests = []
        for variant in variants:
            member_tier = build_member_tier(7, variant)
            for slot, equipment_key in variant.fixed_loadout.model_dump(exclude_none=True).items():
                key = str(equipment_key)
                if key == "shield":
                    continue  # abstract slot — no item to generate
                if key in NATURAL_EQUIPMENT_MAPPINGS:
                    requests.append(
                        build_monster_item_request(
                            owner_key=variant.id,
                            family_id=family.id,
                            member_role=variant.role,
                            member_tier=member_tier,
                            slot=slot,
                            natural_key=key,
                            item_grade="artifact",
                            rarity_tier=7,
                            seed=f"{ANCHOR_PROJECTION_UNIQUE_HASH}:{variant.id}:{slot}",
                            source_context={"variant_key": variant.id, "slot": slot},
                        )
                    )
                else:
                    requests.append(
                        build_monster_item_request(
                            owner_key=variant.id,
                            family_id=family.id,
                            member_role=variant.role,
                            member_tier=member_tier,
                            slot=slot,
                            base_id=key,
                            item_kind=self._item_kind(slot, key),
                            item_grade="artifact",
                            rarity_tier=7,
                            seed=f"{ANCHOR_PROJECTION_UNIQUE_HASH}:{variant.id}:{slot}",
                            source_context={"variant_key": variant.id, "slot": slot},
                        )
                    )
        return list(await self.item_generation.generate_runtime_projections(to_item_generation_requests(requests)))

    @staticmethod
    def _item_kind(slot: str, base_id: str) -> str:
        if base_id == "shield":
            return "shield"
        if slot.endswith("_armor"):
            return "armor"
        return "weapon"
