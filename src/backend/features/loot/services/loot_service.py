from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.loot import resources as loot_resources
from src.backend.features.loot.runtime.loot_engine import LootEngine
from src.shared.schemas.loot import ClaimResultDTO, CorpseDTO, LootContainerDTO, LootTimestamps

if TYPE_CHECKING:
    from src.backend.features.loot.integrations.loot_integration import LootIntegration


class LootService:
    def __init__(self, integration: LootIntegration, engine: LootEngine | None = None) -> None:
        self._integration = integration
        self._engine = engine or LootEngine()

    # ------------------------------------------------------------------
    # Generation - called from loot order handlers
    # ------------------------------------------------------------------

    async def order_loot_for_combat(
        self,
        session_id: str,
        actors: list[dict[str, Any]],
        location_id: str,
        battle_type: str = "",
    ) -> dict[str, str]:
        if not await self._integration.mark_loot_ordered(session_id):
            log.info("LootService | already ordered session={}", session_id)
            return {}

        corpse_ids_by_actor: dict[str, str] = {}
        for actor in actors:
            if actor.get("meta", {}).get("type") != "monster":
                continue
            actor_id = self._actor_id(actor)
            if not actor_id:
                log.warning("LootService | skip corpse without actor_id session={}", session_id)
                continue
            corpse = await self._build_corpse(actor, session_id, battle_type)
            if corpse is None:
                continue
            await self._integration.persist_corpse(corpse, location_id)
            corpse_ids_by_actor[actor_id] = corpse.id
            log.info(
                "LootService | corpse {} for actor={} {} at {}", corpse.id, actor_id, corpse.monster_name, location_id
            )

        return corpse_ids_by_actor

    @staticmethod
    def _actor_id(actor: dict[str, Any]) -> str | None:
        meta = actor.get("meta") if isinstance(actor.get("meta"), dict) else {}
        value = actor.get("actor_id") or meta.get("id") or meta.get("actor_id")
        return str(value) if value is not None else None

    async def _build_corpse(self, actor: dict[str, Any], session_id: str, battle_type: str) -> CorpseDTO | None:
        meta = actor.get("meta", {})
        source = actor.get("source", {})

        profile_id = source.get("loot_profile_id") or source.get("family_id") or "default"
        role = str(meta.get("role") or source.get("member_role") or "minion")
        monster_tier = int(meta.get("tier") or source.get("member_tier") or 0)

        profile = loot_resources.get_profile(profile_id)
        role_profile = profile.get_role(role)

        engine = self._engine

        # Build resource items (drop + salvage + spoil)
        drop_items = engine.build_drop_items(role_profile, monster_tier, role, battle_type)
        salvage_items = engine.build_salvage_items(role_profile, monster_tier, role)
        spoil_items = engine.build_spoil_items(role_profile, monster_tier, role)

        # For humanoids: request equipment instance_ids from Item Service
        equipment_items = [i for i in drop_items if not i.is_resource]
        resource_items = [i for i in drop_items if i.is_resource]

        fulfilled_equipment = []
        for item in equipment_items:
            # Find the matching EquipmentEntry to get exact tier
            eq_tier = engine.roll_equipment_tier(monster_tier, role)
            instance_id = await self._integration.request_item_instance(
                base_id=item.template_id,
                tier=eq_tier,
                source_context={
                    "family_id": profile_id,
                    "member_role": role,
                    "member_tier": monster_tier,
                },
            )
            if instance_id:
                fulfilled_equipment.append(item.model_copy(update={"instance_id": instance_id}))

        all_items = resource_items + fulfilled_equipment + salvage_items + spoil_items
        if not all_items:
            return None

        return CorpseDTO(
            monster_name=meta.get("name", "Monster"),
            items=all_items,
            is_visible=False,
            combat_id=session_id,
            timestamps=LootTimestamps(created_at=time.time()),
        )

    # ------------------------------------------------------------------
    # Activation — called after combat ends
    # ------------------------------------------------------------------

    async def activate_loot(
        self,
        corpse_ids: list[str],
        char_ids: list[int],
        location_id: str,
    ) -> None:
        if not corpse_ids:
            return
        await self._integration.activate_corpses(corpse_ids, char_ids, location_id)
        log.info("LootService | activated {} corpses location={} locked_to={}", len(corpse_ids), location_id, char_ids)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_location_loot(self, location_id: str) -> LootContainerDTO:
        return await self._integration.get_location_loot(location_id)

    # ------------------------------------------------------------------
    # Claim — validation only, ARQ task does the actual transfer
    # ------------------------------------------------------------------

    async def claim_all(self, char_id: int, corpse_ids: list[str]) -> ClaimResultDTO:
        instance_ids: list[str] = []
        resource_deltas: dict[str, int] = {}

        for corpse_id in corpse_ids:
            corpse = await self._integration.get_corpse(corpse_id)
            if corpse is None:
                continue
            if not self._integration.can_claim(corpse, char_id):
                log.info(
                    "LootService | char {} cannot claim corpse {} locked_to={}", char_id, corpse_id, corpse.locked_to
                )
                continue
            for item in corpse.items:
                if item.layer not in ("drop",):  # salvage/spoil require skill check (future)
                    continue
                if item.is_resource:
                    resource_deltas[item.template_id] = resource_deltas.get(item.template_id, 0) + item.amount
                elif item.instance_id:
                    instance_ids.append(item.instance_id)

        return ClaimResultDTO(instance_ids=instance_ids, resource_deltas=resource_deltas)
