from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm.attributes import flag_modified

from src.backend.features.character.models import Character
from src.backend.features.expedition.repository import CharacterExpeditionRepository
from src.backend.features.inventory.repositories.items import InventoryItemRepository, runtime_item_from_instance
from src.backend.features.inventory.services.projection import build_active_character_projection, build_runtime_session
from src.backend.features.items.models import ItemInstance, ItemPlacement, ItemTransaction, ResourceBalance
from src.backend.features.items.models.instance import ResourceTransaction
from src.backend.infrastructure.inventory.models import ResourceWallet
from src.shared.enums import CoreDomain
from src.shared.enums.skill_enums import SkillProgressState
from src.shared.schemas.loot import CorpseDTO, LootItemDTO, LootTimestamps

if TYPE_CHECKING:
    from src.backend.features.expedition.models import CharacterExpedition
    from src.backend.realtime.integrations.notice_publisher import PlayerNoticePublisher

_CURRENCY_PREFIXES = ("coin_", "currency_", "gold_", "silver_", "copper_")
_COMPONENT_PREFIXES = ("essence_", "flower_", "bark_", "supply_", "component_")


class ExpeditionService:
    """Lifecycle service for dirty gains outside system-connect locations."""

    def __init__(
        self,
        *,
        session,
        character_sessions=None,
        expedition_repo: CharacterExpeditionRepository | None = None,
        expedition_manager=None,
        loot_manager=None,
        world_store=None,
        commit_on_write: bool = False,
        game_config: Any | None = None,
        notice_publisher: PlayerNoticePublisher | None = None,
    ) -> None:
        self.session = session
        self.character_sessions = character_sessions
        self.expedition_repo = expedition_repo or CharacterExpeditionRepository(session)
        self.expedition_manager = expedition_manager
        self.loot_manager = loot_manager
        self.world_store = world_store
        self.commit_on_write = commit_on_write
        self._game_config = game_config
        self.notice_publisher = notice_publisher

    @staticmethod
    def has_system_connect(flags: dict[str, Any] | None) -> bool:
        flags = flags if isinstance(flags, dict) else {}
        return bool(flags.get("system_connect") or flags.get("is_safe_zone"))

    async def get_active_run(self, char_id: int, *, for_update: bool = False) -> CharacterExpedition | None:
        return await self.expedition_repo.get_active_for_character(char_id, for_update=for_update)

    async def is_active_unsafe(self, char_id: int) -> bool:
        return await self.get_active_run(char_id) is not None

    async def handle_location_transition(
        self,
        *,
        char_id: int,
        from_loc: str | None,
        to_loc: str,
        target_loc_data: dict[str, Any] | None,
    ) -> CharacterExpedition | None:
        flags = (target_loc_data or {}).get("flags")
        if self.has_system_connect(flags if isinstance(flags, dict) else {}):
            location_name = (target_loc_data or {}).get("name") if isinstance(target_loc_data, dict) else None
            await self.safe_sync(char_id=char_id, location_id=to_loc, location_name=location_name)
            return None

        expedition = await self.get_active_run(char_id, for_update=True)
        if expedition is None:
            anchor = await self._respawn_anchor(char_id)
            expedition = await self.expedition_repo.create_active(
                char_id=char_id,
                start_location_id=from_loc or to_loc,
                current_location_id=to_loc,
                respawn_anchor_location_id=anchor,
            )
            logger.bind(char_id=char_id, run_id=expedition.run_id, location_id=to_loc).info("ExpeditionStarted")
        else:
            expedition.current_location_id = to_loc

        await self._cache_active_run(expedition)
        await self.refresh_session_risk(char_id, expedition=expedition, system_connect=False)
        await self._maybe_commit()
        return expedition

    async def apply_progress(self, char_id: int, rewards: dict[str, float]) -> bool:
        expedition = await self.get_active_run(char_id, for_update=True)
        if expedition is None or expedition.status != "active":
            return False

        pending = self._pending(expedition)
        skills = dict(pending.get("skills") or {})
        free_xp = float(pending.get("free_xp", 0.0) or 0.0)
        for key, raw_delta in rewards.items():
            delta = round(float(raw_delta or 0.0), 4)
            if delta <= 0:
                continue
            if key == "free_xp":
                free_xp = round(free_xp + delta, 4)
            else:
                skills[str(key)] = round(float(skills.get(str(key), 0.0) or 0.0) + delta, 4)

        pending["skills"] = skills
        pending["free_xp"] = free_xp
        expedition.pending_progress_json = pending
        flag_modified(expedition, "pending_progress_json")

        if self.character_sessions is not None:
            await self.character_sessions.apply_pending_progress(char_id, rewards)
            await self.refresh_session_risk(char_id, expedition=expedition, system_connect=False)
        return True

    async def safe_sync(self, *, char_id: int, location_id: str, location_name: str | None = None) -> None:
        expedition = await self.get_active_run(char_id, for_update=True)
        if expedition is None:
            await self.refresh_session_risk(char_id, expedition=None, system_connect=True)
            return
        if expedition.status != "active":
            await self.refresh_session_risk(char_id, expedition=expedition, system_connect=True)
            return

        pending = self._pending(expedition)
        secured_items = await self._secure_expedition_items(expedition)
        await self._secure_expedition_resources(expedition)
        await self._persist_pending_progress(char_id, pending)
        character = await self.session.get(Character, char_id)
        if character is not None:
            character.location_id = location_id
            character.prev_location_id = expedition.current_location_id
            character.game_stage = CoreDomain.EXPLORATION.value

        expedition.status = "synced"
        expedition.ended_at = datetime.now(UTC)
        expedition.current_location_id = location_id
        expedition.pending_progress_json = {}
        flag_modified(expedition, "pending_progress_json")

        if self.expedition_manager is not None:
            await self.expedition_manager.clear_active_run(char_id)
            await self.expedition_manager.delete_runtime(expedition.run_id)

        if self.character_sessions is not None:
            await self._merge_pending_into_active_session(char_id, pending)
            await self._refresh_active_items(char_id)
            await self.character_sessions.set_pending_progress(char_id, self._empty_pending())
            await self.refresh_session_risk(char_id, expedition=None, system_connect=True)

        logger.bind(char_id=char_id, run_id=expedition.run_id, location_id=location_id).info("ExpeditionSynced")
        await self._maybe_commit()

        if self.notice_publisher is not None:
            await self.notice_publisher.safe_zone_entered(char_id, location_name=location_name)
            if secured_items:
                await self.notice_publisher.items_secured(char_id, count=secured_items)

    async def mark_death_pending(
        self,
        *,
        char_id: int,
        combat_id: str | None,
        location_id: str | None,
    ) -> bool:
        expedition = await self.get_active_run(char_id, for_update=True)
        if expedition is None or expedition.status != "active":
            return False

        expedition.status = "death_pending"
        expedition.death_combat_id = combat_id
        expedition.death_event_id = f"death:{combat_id or uuid.uuid4().hex}:{char_id}"
        if location_id:
            expedition.current_location_id = location_id

        if self.character_sessions is not None:
            await self.character_sessions.patch_fields(
                char_id,
                {
                    "$.state": CoreDomain.COMBAT_RESULT.value,
                    "$.prev_state": CoreDomain.COMBAT.value,
                    "$.sessions.combat_id": None,
                    "$.sessions.combat_finalization_id": str(combat_id) if combat_id else None,
                    "$.sessions.death_run_id": expedition.run_id,
                    "$.sessions.death_corpse_id": expedition.corpse_id,
                },
            )
            await self.character_sessions.mark_dirty(
                char_id,
                reason="expedition_death_pending",
                paths=[
                    "$.prev_state",
                    "$.sessions.combat_finalization_id",
                    "$.sessions.combat_id",
                    "$.sessions.death_run_id",
                    "$.state",
                ],
            )
            await self.refresh_session_risk(char_id, expedition=expedition, system_connect=False)
        await self._maybe_commit()
        if self.notice_publisher is not None:
            await self.notice_publisher.player_died(char_id)
        return True

    async def finalize_death_corpse(self, *, char_id: int) -> dict[str, Any]:
        expedition = await self.get_active_run(char_id, for_update=True)
        if expedition is None or expedition.status != "death_pending":
            return {"status": "no_death_pending", "corpse_id": None}

        processed_key = f"death_corpse:{expedition.run_id}"
        if self.expedition_repo.is_processed(expedition, processed_key) and expedition.corpse_id:
            await self._patch_death_corpse_session(char_id, expedition)
            return {"status": "already_finalized", "corpse_id": expedition.corpse_id}

        corpse_ttl = 86400.0
        if self._game_config is not None:
            corpse_ttl = await self._game_config.get_float("expedition", "PLAYER_CORPSE_TTL_SECONDS", default=86400.0)

        corpse_id = expedition.corpse_id or uuid.uuid4().hex
        corpse_location_id = expedition.current_location_id or "52_52"
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=corpse_ttl)

        item_rows = await self._move_expedition_items_to_corpse(expedition, corpse_id)
        resource_rows = await self._move_expedition_resources_to_corpse(expedition, corpse_id)

        expedition.corpse_id = corpse_id
        expedition.corpse_location_id = corpse_location_id
        expedition.corpse_public_at = now
        expedition.corpse_expires_at = expires_at
        expedition.pending_progress_json = {}
        flag_modified(expedition, "pending_progress_json")
        self.expedition_repo.mark_processed(
            expedition,
            processed_key,
            {
                "corpse_id": corpse_id,
                "location_id": corpse_location_id,
                "item_count": len(item_rows),
                "resource_count": len(resource_rows),
            },
        )
        flag_modified(expedition, "processed_events")

        await self._persist_player_corpse(
            expedition,
            item_rows=item_rows,
            resource_rows=resource_rows,
            now_ts=now.timestamp(),
            expires_ts=expires_at.timestamp(),
            corpse_ttl=corpse_ttl,
        )
        await self._patch_death_corpse_session(char_id, expedition)
        await self._maybe_commit()
        logger.bind(char_id=char_id, run_id=expedition.run_id, corpse_id=corpse_id).info(
            "ExpeditionDeathCorpseFinalized"
        )
        if self.notice_publisher is not None and (item_rows or resource_rows):
            await self.notice_publisher.corpse_items_lost(char_id, count=len(item_rows))
        return {"status": "finalized", "corpse_id": corpse_id, "location_id": corpse_location_id}

    async def respawn(self, *, char_id: int) -> dict[str, Any]:
        expedition = await self.get_active_run(char_id, for_update=True)
        if expedition is None:
            return {"status": "no_active_expedition", "target_state": CoreDomain.EXPLORATION.value}

        processed_key = f"respawn:{expedition.run_id}"
        if self.expedition_repo.is_processed(expedition, processed_key):
            await self._restore_active_session_after_respawn(char_id, expedition)
            return self._respawn_result(expedition)

        now = datetime.now(UTC)
        death_corpse_key = f"death_corpse:{expedition.run_id}"
        if not self.expedition_repo.is_processed(expedition, death_corpse_key):
            await self.finalize_death_corpse(char_id=char_id)
        expedition.status = "dead"
        expedition.ended_at = now
        expedition.pending_progress_json = {}
        flag_modified(expedition, "pending_progress_json")
        self.expedition_repo.mark_processed(expedition, processed_key)
        flag_modified(expedition, "processed_events")

        if self.expedition_manager is not None:
            await self.expedition_manager.clear_active_run(char_id)
            await self.expedition_manager.delete_runtime(expedition.run_id)

        await self._restore_active_session_after_respawn(char_id, expedition)
        await self._maybe_commit()
        logger.bind(char_id=char_id, run_id=expedition.run_id, corpse_id=expedition.corpse_id).info(
            "ExpeditionRespawned"
        )
        if self.notice_publisher is not None:
            await self.notice_publisher.player_respawned(char_id)
        return self._respawn_result(expedition)

    async def refresh_session_risk(
        self,
        char_id: int,
        *,
        expedition: CharacterExpedition | None,
        system_connect: bool,
    ) -> None:
        if self.character_sessions is None:
            return
        if expedition is None:
            await self.character_sessions.set_risk_state(
                char_id,
                {
                    "sync_state": "safe",
                    "system_connect": bool(system_connect),
                    "run_id": None,
                    "corpse_id": None,
                    "pending_free_xp": 0.0,
                    "pending_skill_count": 0,
                    "carried_resource_count": 0,
                    "carried_item_count": 0,
                },
            )
            return

        pending = self._pending(expedition)
        await self.character_sessions.set_pending_progress(char_id, pending)
        await self.character_sessions.set_risk_state(
            char_id,
            {
                "sync_state": "death" if expedition.status == "death_pending" else "unsafe",
                "system_connect": bool(system_connect),
                "run_id": expedition.run_id,
                "corpse_id": expedition.corpse_id,
                "pending_free_xp": round(float(pending.get("free_xp", 0.0) or 0.0), 4),
                "pending_skill_count": len(pending.get("skills") or {}),
                "carried_resource_count": await self._count_expedition_resources(expedition.run_id),
                "carried_item_count": await self._count_expedition_items(expedition.run_id),
            },
        )

    async def _respawn_anchor(self, char_id: int) -> str:
        character = await self.session.get(Character, char_id)
        if character is None:
            return "52_52"
        return character.respawn_anchor_location_id or "52_52"

    async def _cache_active_run(self, expedition: CharacterExpedition) -> None:
        if self.expedition_manager is None:
            return
        await self.expedition_manager.set_active_run(expedition.character_id, expedition.run_id)
        await self.expedition_manager.save_runtime(
            expedition.run_id,
            {
                "run_id": expedition.run_id,
                "char_id": expedition.character_id,
                "status": expedition.status,
                "current_location_id": expedition.current_location_id,
                "pending_progress": self._pending(expedition),
            },
        )

    async def _secure_expedition_items(self, expedition: CharacterExpedition) -> int:
        placements = list(
            (
                await self.session.scalars(
                    select(ItemPlacement).where(
                        ItemPlacement.holder_type == "expedition",
                        ItemPlacement.holder_id == expedition.run_id,
                    )
                )
            ).all()
        )
        for placement in placements:
            self.session.add(
                ItemTransaction(
                    item_id=placement.item_id,
                    from_holder_type=placement.holder_type,
                    from_holder_id=placement.holder_id,
                    from_storage_type=placement.storage_type,
                    to_holder_type="character",
                    to_holder_id=str(expedition.character_id),
                    to_storage_type=placement.storage_type,
                    reason="expedition_safe_sync",
                    correlation_id=expedition.run_id,
                )
            )
            placement.holder_type = "character"
            placement.holder_id = str(expedition.character_id)
            placement.locked_by = None
        return len(placements)

    async def _secure_expedition_resources(self, expedition: CharacterExpedition) -> None:
        balances = list(
            (
                await self.session.scalars(
                    select(ResourceBalance).where(
                        ResourceBalance.holder_type == "expedition",
                        ResourceBalance.holder_id == expedition.run_id,
                    )
                )
            ).all()
        )
        if not balances:
            return

        wallet = await self._wallet_for_update(expedition.character_id)
        for balance in balances:
            amount = int(balance.amount or 0)
            if amount <= 0:
                await self.session.delete(balance)
                continue
            bucket = self._wallet_bucket(wallet, balance.resource_key)
            bucket[balance.resource_key] = int(bucket.get(balance.resource_key, 0) or 0) + amount
            self.session.add(
                ResourceTransaction(
                    resource_key=balance.resource_key,
                    amount=amount,
                    from_holder_type=balance.holder_type,
                    from_holder_id=balance.holder_id,
                    from_storage_type=balance.storage_type,
                    to_holder_type="character",
                    to_holder_id=str(expedition.character_id),
                    to_storage_type="wallet",
                    reason="expedition_safe_sync",
                    correlation_id=expedition.run_id,
                )
            )
            await self.session.delete(balance)

        flag_modified(wallet, "currency")
        flag_modified(wallet, "resources")
        flag_modified(wallet, "components")

    async def _persist_pending_progress(self, char_id: int, pending: dict[str, Any]) -> None:
        free_xp = float(pending.get("free_xp", 0.0) or 0.0)
        if free_xp > 0:
            from src.backend.features.character.repositories import CharacterProgressionRepository

            await CharacterProgressionRepository(self.session).increment_free_xp(char_id, free_xp)

        skills = pending.get("skills") if isinstance(pending.get("skills"), dict) else {}
        rows = [
            {
                "character_id": char_id,
                "skill_key": str(skill_key),
                "total_xp": round(float(delta or 0.0), 4),
                "is_unlocked": True,
                "progress_state": SkillProgressState.PLUS,
            }
            for skill_key, delta in skills.items()
            if float(delta or 0.0) > 0
        ]
        if rows:
            from src.backend.features.character.repositories import SkillRepository

            await SkillRepository(self.session).increment_progress_rows(rows)

    async def _merge_pending_into_active_session(self, char_id: int, pending: dict[str, Any]) -> None:
        if self.character_sessions is None:
            return
        rewards = dict(pending.get("skills") or {})
        free_xp = float(pending.get("free_xp", 0.0) or 0.0)
        if free_xp > 0:
            rewards["free_xp"] = free_xp
        if rewards:
            await self.character_sessions.apply_skill_progress(char_id, rewards)

    async def _move_expedition_items_to_corpse(
        self,
        expedition: CharacterExpedition,
        corpse_id: str,
    ) -> list[tuple[ItemInstance, ItemPlacement]]:
        rows = list(
            (
                await self.session.execute(
                    select(ItemInstance, ItemPlacement)
                    .join(ItemPlacement, ItemPlacement.item_id == ItemInstance.id)
                    .where(
                        ItemPlacement.holder_type == "expedition",
                        ItemPlacement.holder_id == expedition.run_id,
                    )
                )
            ).all()
        )
        for _instance, placement in rows:
            self.session.add(
                ItemTransaction(
                    item_id=placement.item_id,
                    from_holder_type=placement.holder_type,
                    from_holder_id=placement.holder_id,
                    from_storage_type=placement.storage_type,
                    to_holder_type="corpse",
                    to_holder_id=corpse_id,
                    to_storage_type=placement.storage_type or "backpack",
                    reason="player_death_drop",
                    correlation_id=expedition.run_id,
                )
            )
            placement.holder_type = "corpse"
            placement.holder_id = corpse_id
            placement.slot = None
            placement.position_index = None
            placement.locked_by = None
        return rows

    async def _move_expedition_resources_to_corpse(
        self,
        expedition: CharacterExpedition,
        corpse_id: str,
    ) -> list[ResourceBalance]:
        balances = list(
            (
                await self.session.scalars(
                    select(ResourceBalance).where(
                        ResourceBalance.holder_type == "expedition",
                        ResourceBalance.holder_id == expedition.run_id,
                    )
                )
            ).all()
        )
        for balance in balances:
            self.session.add(
                ResourceTransaction(
                    resource_key=balance.resource_key,
                    amount=int(balance.amount or 0),
                    from_holder_type=balance.holder_type,
                    from_holder_id=balance.holder_id,
                    from_storage_type=balance.storage_type,
                    to_holder_type="corpse",
                    to_holder_id=corpse_id,
                    to_storage_type="carried",
                    reason="player_death_drop",
                    correlation_id=expedition.run_id,
                )
            )
            balance.holder_type = "corpse"
            balance.holder_id = corpse_id
            balance.storage_type = "carried"
            balance.locked_amount = 0
        return balances

    async def _persist_player_corpse(
        self,
        expedition: CharacterExpedition,
        *,
        item_rows: list[tuple[ItemInstance, ItemPlacement]],
        resource_rows: list[ResourceBalance],
        now_ts: float,
        expires_ts: float,
        corpse_ttl: float,
    ) -> None:
        if self.loot_manager is None or expedition.corpse_id is None or expedition.corpse_location_id is None:
            return

        loot_items = [
            LootItemDTO(
                template_id=instance.base_id,
                name=instance.name,
                rarity=instance.rarity,
                amount=1,
                layer="drop",
                instance_id=str(instance.id),
                is_resource=False,
                metadata={"source": "player_corpse", "run_id": expedition.run_id},
            )
            for instance, _placement in item_rows
        ]
        loot_items.extend(
            LootItemDTO(
                template_id=balance.resource_key,
                name=balance.resource_key.replace("_", " ").title(),
                amount=max(0, int(balance.amount or 0)),
                layer="drop",
                is_resource=True,
                metadata={"source": "player_corpse", "run_id": expedition.run_id},
            )
            for balance in resource_rows
            if int(balance.amount or 0) > 0
        )

        corpse = CorpseDTO(
            id=expedition.corpse_id,
            monster_name="Player remains",
            items=loot_items,
            is_visible=True,
            locked_to=[expedition.character_id],
            combat_id=expedition.death_combat_id,
            corpse_type="player",
            owner_char_id=expedition.character_id,
            source_run_id=expedition.run_id,
            access_policy={"owner_lock": True, "public_delay_seconds": 0, "ttl_seconds": corpse_ttl},
            timestamps=LootTimestamps(created_at=now_ts, public_at=now_ts, decay_at=expires_ts),
        )
        await self.loot_manager.save_corpse(corpse, expedition.corpse_location_id, corpse_ttl)

    async def _patch_death_corpse_session(self, char_id: int, expedition: CharacterExpedition) -> None:
        if self.character_sessions is None:
            return
        await self.character_sessions.patch_fields(
            char_id,
            {
                "$.sessions.death_run_id": expedition.run_id,
                "$.sessions.death_corpse_id": expedition.corpse_id,
                "$.pending_progress": self._empty_pending(),
            },
        )
        await self.character_sessions.set_pending_progress(char_id, self._empty_pending())
        await self.refresh_session_risk(char_id, expedition=expedition, system_connect=False)

    async def _restore_active_session_after_respawn(
        self,
        char_id: int,
        expedition: CharacterExpedition,
    ) -> None:
        if self.character_sessions is None:
            return
        anchor = expedition.respawn_anchor_location_id or "52_52"
        await self.character_sessions.patch_fields(
            char_id,
            {
                "$.state": CoreDomain.EXPLORATION.value,
                "$.prev_state": CoreDomain.DEATH.value,
                "$.location.current": anchor,
                "$.location.prev": expedition.current_location_id,
                "$.sessions.combat_id": None,
                "$.sessions.combat_finalization_id": None,
                "$.sessions.death_run_id": None,
                "$.sessions.death_corpse_id": expedition.corpse_id,
                "$.pending_progress": self._empty_pending(),
            },
        )
        restored_vitals = await self.character_sessions.restore_vitals_to_max(char_id)
        character = await self.session.get(Character, char_id)
        if character is not None:
            character.game_stage = CoreDomain.EXPLORATION.value
            character.prev_game_stage = CoreDomain.DEATH.value
            character.location_id = anchor
            character.prev_location_id = expedition.current_location_id
            character.vitals_snapshot = restored_vitals
            character.active_sessions = {
                "combat_id": None,
                "combat_finalization_id": None,
                "death_run_id": None,
                "death_corpse_id": expedition.corpse_id,
            }
        await self.character_sessions.mark_dirty(
            char_id,
            reason="expedition_respawned",
            paths=[
                "$.location.current",
                "$.location.prev",
                "$.prev_state",
                "$.sessions.combat_finalization_id",
                "$.sessions.combat_id",
                "$.sessions.death_corpse_id",
                "$.sessions.death_run_id",
                "$.state",
            ],
        )
        if self.world_store is not None:
            if expedition.current_location_id:
                await self.world_store.remove_player(expedition.current_location_id, char_id)
            await self.world_store.add_player(anchor, char_id)
        await self._refresh_active_items(char_id)
        await self.refresh_session_risk(char_id, expedition=None, system_connect=True)

    async def _wallet_for_update(self, char_id: int) -> ResourceWallet:
        wallet = await self.session.scalar(
            select(ResourceWallet).where(ResourceWallet.character_id == char_id).with_for_update()
        )
        if wallet is not None:
            return wallet
        wallet = ResourceWallet(character_id=char_id, currency={}, resources={}, components={})
        self.session.add(wallet)
        await self.session.flush()
        return wallet

    async def _refresh_active_items(self, char_id: int) -> None:
        if self.character_sessions is None:
            return
        rows = await InventoryItemRepository(self.session).list_character_items(char_id)
        runtime_items = [runtime_item_from_instance(instance, placement) for instance, placement in rows]
        inventory_session = build_runtime_session(char_id, runtime_items)
        projection = build_active_character_projection(inventory_session)
        await self.character_sessions.set_items_projection(char_id, projection.model_dump(mode="json"))

    @staticmethod
    def _wallet_bucket(wallet: ResourceWallet, key: str) -> dict[str, int]:
        if key.startswith(_CURRENCY_PREFIXES):
            return wallet.currency
        if key.startswith(_COMPONENT_PREFIXES):
            return wallet.components
        return wallet.resources

    async def _count_expedition_items(self, run_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ItemPlacement)
            .where(
                ItemPlacement.holder_type == "expedition",
                ItemPlacement.holder_id == run_id,
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_expedition_resources(self, run_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ResourceBalance)
            .where(
                ResourceBalance.holder_type == "expedition",
                ResourceBalance.holder_id == run_id,
                ResourceBalance.amount > 0,
            )
        )
        return int(result.scalar_one() or 0)

    @staticmethod
    def _pending(expedition: CharacterExpedition) -> dict[str, Any]:
        pending = dict(expedition.pending_progress_json or {})
        pending.setdefault("free_xp", 0.0)
        pending.setdefault("skills", {})
        pending.setdefault("weapon", {})
        pending.setdefault("armor", {})
        pending.setdefault("symbiote", {})
        return pending

    @staticmethod
    def _empty_pending() -> dict[str, Any]:
        return {"free_xp": 0.0, "skills": {}, "weapon": {}, "armor": {}, "symbiote": {}}

    @staticmethod
    def _respawn_result(expedition: CharacterExpedition) -> dict[str, Any]:
        return {
            "status": "respawned",
            "target_state": CoreDomain.EXPLORATION.value,
            "location_id": expedition.respawn_anchor_location_id or "52_52",
            "corpse_id": expedition.corpse_id,
            "run_id": expedition.run_id,
        }

    async def _maybe_commit(self) -> None:
        if self.commit_on_write:
            await self.session.commit()


async def increment_expedition_resource(
    session,
    *,
    run_id: str,
    resource_key: str,
    amount: int,
    reason: str,
    correlation_id: str | None = None,
) -> None:
    if amount <= 0:
        return
    stmt = insert(ResourceBalance).values(
        holder_type="expedition",
        holder_id=run_id,
        storage_type="carried",
        resource_key=resource_key,
        amount=int(amount),
        locked_amount=0,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_resource_balance_place",
        set_={"amount": ResourceBalance.amount + stmt.excluded.amount},
    )
    await session.execute(stmt)
    session.add(
        ResourceTransaction(
            resource_key=resource_key,
            amount=int(amount),
            to_holder_type="expedition",
            to_holder_id=run_id,
            to_storage_type="carried",
            reason=reason,
            correlation_id=correlation_id,
        )
    )


async def delete_expedition_resource_balances(session, run_id: str) -> None:
    await session.execute(
        delete(ResourceBalance).where(
            ResourceBalance.holder_type == "expedition",
            ResourceBalance.holder_id == run_id,
        )
    )
