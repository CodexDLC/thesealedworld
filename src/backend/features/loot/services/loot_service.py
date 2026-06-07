from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.backend.features.loot import resources as loot_resources
from src.backend.features.loot.runtime.loot_engine import LootEngine
from src.shared.schemas.loot import ClaimResultDTO, CorpseDTO, LootContainerDTO, LootTimestamps

if TYPE_CHECKING:
    from src.backend.features.loot.integrations.loot_integration import LootIntegration


_RIFT_GROUP_DROP_STEP = 0.10
_RIFT_GROUP_DROP_MAX_MULTIPLIER = 1.50


@dataclass(frozen=True)
class _LootDropContext:
    monster_count: int
    group_bonus_multiplier: float = 1.0


@dataclass(frozen=True)
class _EquipmentDropCandidate:
    actor: dict[str, Any]
    profile_id: str
    role: str
    monster_tier: int
    location_id: str
    eq_profile: loot_resources.FamilyEquipmentProfile


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
            log.bind(session_id=session_id).debug("LootServiceAlreadyOrdered")
            return {}

        corpse_ids_by_actor: dict[str, str] = {}
        try:
            drop_context = self._build_drop_context(actors, battle_type)
            equipment_candidates: list[_EquipmentDropCandidate] = []
            built_corpses: list[tuple[str, CorpseDTO, str]] = []
            corpse_by_actor: dict[str, CorpseDTO] = {}
            for actor in actors:
                if actor.get("meta", {}).get("type") != "monster":
                    continue
                actor_id = self._actor_id(actor)
                if not actor_id:
                    log.bind(session_id=session_id).warning("LootCorpseSkipped")
                    continue
                corpse = await self._build_corpse(
                    actor,
                    session_id,
                    battle_type,
                    location_id,
                    drop_context=drop_context,
                    equipment_candidates=equipment_candidates,
                )
                if corpse is None:
                    continue
                built_corpses.append((actor_id, corpse, location_id))
                corpse_by_actor[actor_id] = corpse
                corpse_ids_by_actor[actor_id] = corpse.id

            if drop_context.group_bonus_multiplier > 1.0:
                bonus = await self._build_group_bonus_equipment_corpse(
                    equipment_candidates,
                    session_id=session_id,
                    drop_context=drop_context,
                )
                if bonus is not None:
                    actor_id, corpse, location_id = bonus
                    existing = corpse_by_actor.get(actor_id)
                    if existing is not None:
                        existing.items.extend(corpse.items)
                    else:
                        built_corpses.append((actor_id, corpse, location_id))
                        corpse_by_actor[actor_id] = corpse
                        corpse_ids_by_actor[actor_id] = corpse.id

            for actor_id, corpse, corpse_location_id in built_corpses:
                await self._integration.persist_corpse(corpse, corpse_location_id)
                log.bind(
                    corpse_id=corpse.id,
                    actor_id=actor_id,
                    monster_name=corpse.monster_name,
                    location_id=corpse_location_id,
                ).info("LootCorpseCreated")
        except Exception:
            await self._clear_order_marker(session_id)
            raise

        if not corpse_ids_by_actor:
            await self._clear_order_marker(session_id)

        return corpse_ids_by_actor

    async def _clear_order_marker(self, session_id: str) -> None:
        clear = getattr(self._integration, "clear_loot_ordered", None)
        if clear is not None:
            await clear(session_id)

    @staticmethod
    def _actor_id(actor: dict[str, Any]) -> str | None:
        meta = actor.get("meta") if isinstance(actor.get("meta"), dict) else {}
        value = actor.get("actor_id") or meta.get("id") or meta.get("actor_id")
        return str(value) if value is not None else None

    async def _build_corpse(
        self,
        actor: dict[str, Any],
        session_id: str,
        battle_type: str,
        location_id: str,
        *,
        drop_context: _LootDropContext,
        equipment_candidates: list[_EquipmentDropCandidate],
    ) -> CorpseDTO | None:
        meta = actor.get("meta", {})
        source = actor.get("source", {})

        profile_id = source.get("loot_profile_id") or source.get("family_id") or "default"
        role = str(meta.get("role") or source.get("member_role") or "minion")
        monster_tier = int(meta.get("tier") or source.get("member_tier") or 0)

        profile = loot_resources.get_profile(profile_id)
        role_profile = profile.get_role(role)

        engine = self._engine

        # Ordinary post-combat loot only materializes plain drop.
        # Salvage/spoil require explicit future actions and skills/tools.
        drop_items = engine.build_drop_items(
            role_profile,
            monster_tier,
            role,
            battle_type,
            chance_multiplier=1.0,
        )
        resource_items = list(drop_items)

        # Pool-based equipment roll — one item per monster, chance driven by family config
        fulfilled_equipment = []
        if profile.equipment is not None:
            equipment_candidates.append(
                _EquipmentDropCandidate(
                    actor=actor,
                    profile_id=str(profile_id),
                    role=role,
                    monster_tier=monster_tier,
                    location_id=location_id,
                    eq_profile=profile.equipment,
                )
            )
            base_id = engine.pick_equipment_base_id(
                profile.equipment,
                role,
                chance_multiplier=1.0,
            )
            if base_id is not None:
                eq_tier = engine.roll_equipment_tier(monster_tier, role)
                instance_id = await self._integration.request_item_instance(
                    base_id=base_id,
                    tier=eq_tier,
                    source_context=self._item_source_context(
                        source=source,
                        profile_id=str(profile_id),
                        location_id=location_id,
                        monster_tier=monster_tier,
                    ),
                )
                if instance_id:
                    from src.shared.schemas.loot import LootItemDTO  # noqa: PLC0415

                    fulfilled_equipment.append(
                        LootItemDTO(
                            template_id=base_id,
                            name=base_id,
                            layer="drop",
                            is_resource=False,
                            instance_id=instance_id,
                        )
                    )

        all_items = resource_items + fulfilled_equipment
        if not all_items:
            return None

        return CorpseDTO(
            monster_name=meta.get("name", "Monster"),
            items=all_items,
            is_visible=False,
            combat_id=session_id,
            timestamps=LootTimestamps(created_at=time.time()),
        )

    async def _build_group_bonus_equipment_corpse(
        self,
        candidates: list[_EquipmentDropCandidate],
        *,
        session_id: str,
        drop_context: _LootDropContext,
    ) -> tuple[str, CorpseDTO, str] | None:
        bonus = self._engine.build_group_bonus_item(
            candidates,
            chance_multiplier=drop_context.group_bonus_multiplier,
        )
        if bonus is None:
            return None
        candidate, base_id = bonus
        actor_id = self._actor_id(candidate.actor)
        if not actor_id:
            return None
        source = candidate.actor.get("source", {})
        eq_tier = self._engine.roll_equipment_tier(candidate.monster_tier, candidate.role)
        instance_id = await self._integration.request_item_instance(
            base_id=base_id,
            tier=eq_tier,
            source_context=self._item_source_context(
                source=source,
                profile_id=candidate.profile_id,
                location_id=candidate.location_id,
                monster_tier=candidate.monster_tier,
            ),
        )
        if not instance_id:
            return None

        from src.shared.schemas.loot import LootItemDTO  # noqa: PLC0415

        meta = candidate.actor.get("meta", {})
        corpse = CorpseDTO(
            monster_name=meta.get("name", "Monster"),
            items=[
                LootItemDTO(
                    template_id=base_id,
                    name=base_id,
                    layer="drop",
                    is_resource=False,
                    instance_id=instance_id,
                )
            ],
            is_visible=False,
            combat_id=session_id,
            timestamps=LootTimestamps(created_at=time.time()),
        )
        return actor_id, corpse, candidate.location_id

    @staticmethod
    def _build_drop_context(actors: list[dict[str, Any]], battle_type: str) -> _LootDropContext:
        monster_count = sum(1 for actor in actors if (actor.get("meta") or {}).get("type") == "monster")
        if battle_type.lower() != "rift" or monster_count <= 1:
            return _LootDropContext(monster_count=monster_count)
        multiplier = min(
            _RIFT_GROUP_DROP_MAX_MULTIPLIER,
            1.0 + ((monster_count - 1) * _RIFT_GROUP_DROP_STEP),
        )
        return _LootDropContext(
            monster_count=monster_count,
            group_bonus_multiplier=round(multiplier, 2),
        )

    @staticmethod
    def _item_source_context(
        *,
        source: dict[str, Any],
        profile_id: str,
        location_id: str,
        monster_tier: int,
    ) -> dict[str, Any]:
        owner_family = source.get("owner_family")
        source_context: dict[str, Any] = {
            "family_id": source.get("family_id") or profile_id,
            "monster_family_id": source.get("family_id") or profile_id,
            "location_id": location_id,
            "source_tier": monster_tier,
        }
        clan_id = source.get("clan_id")
        if clan_id:
            source_context["clan_id"] = str(clan_id)
        if isinstance(owner_family, dict):
            source_context["owner_family"] = dict(owner_family)
        return source_context

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
        log.bind(corpse_count=len(corpse_ids), location_id=location_id, char_ids=char_ids).info(
            "LootServiceCorpsesActivated"
        )

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
        summary_items: list[str] = []

        for corpse_id in corpse_ids:
            corpse = await self._integration.get_corpse(corpse_id)
            if corpse is None:
                continue
            if not self._integration.can_claim(corpse, char_id):
                log.bind(char_id=char_id, corpse_id=corpse_id, locked_to=corpse.locked_to).info("LootCorpseClaimDenied")
                continue
            for item in corpse.items:
                if item.layer not in ("drop",):  # salvage/spoil require skill check (future)
                    continue
                if item.is_resource:
                    resource_deltas[item.template_id] = resource_deltas.get(item.template_id, 0) + item.amount
                    summary_items.append(_loot_summary_label(item.name, item.amount))
                elif item.instance_id:
                    instance_ids.append(item.instance_id)
                    summary_items.append(_loot_summary_label(item.name, item.amount))

        return ClaimResultDTO(instance_ids=instance_ids, resource_deltas=resource_deltas, summary_items=summary_items)


def _loot_summary_label(name: str, amount: int) -> str:
    label = str(name or "Добыча").strip() or "Добыча"
    count = max(1, int(amount or 1))
    return f"{label} x{count}" if count > 1 else label
