from __future__ import annotations

import hashlib
import json
from typing import Any

from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.orm.attributes import flag_modified

from src.backend.core.database import get_session_context
from src.backend.features.expedition import ExpeditionService
from src.backend.features.expedition.service import increment_expedition_resource
from src.backend.features.items.models import ItemPlacement, ResourceBalance
from src.backend.features.loot.integrations.loot_integration import LootIntegration
from src.backend.infrastructure.inventory.managers import InventorySessionManager
from src.backend.infrastructure.inventory.models import ResourceWallet
from src.backend.infrastructure.loot.managers.loot_manager import LootManager
from src.shared.infrastructure.log_task_wrapper import logged_task
from src.shared.schemas.loot import ClaimResultDTO

_CURRENCY_PREFIXES = ("coin_", "currency_", "gold_", "silver_", "copper_")
_COMPONENT_PREFIXES = ("essence_", "flower_", "bark_", "supply_", "component_")


@logged_task
async def loot_claim_task(ctx: dict[str, Any], payload: dict[str, Any]) -> None:
    """
    ARQ coordinator for atomic loot claiming.

    Order: PostgreSQL first, Redis after.
    If PG fails → ARQ retries, corpse remains untouched (idempotent).

    payload:
        char_id         — character picking up the loot
        corpse_id       — single corpse being claimed
        instance_ids    — list of ItemInstance UUIDs to transfer
        resource_deltas — {template_id: amount} for ResourceWallet increment
    """
    char_id: int = int(payload.get("char_id", 0))
    corpse_id: str = str(payload.get("corpse_id", ""))
    instance_ids: list[str] = payload.get("instance_ids") or []
    resource_deltas: dict[str, int] = payload.get("resource_deltas") or {}

    if not char_id or not corpse_id:
        log.error("LootClaimPayloadInvalid")
        return

    log.bind(
        char_id=char_id,
        corpse_id=corpse_id,
        item_count=len(instance_ids),
        resource_count=len(resource_deltas),
    ).info("LootClaimTaskStarted")

    redis_service = ctx.get("redis_service")
    if redis_service is None:
        log.error("LootClaimRedisServiceMissing")
        return

    # -----------------------------------------------------------------
    # Step 1: PostgreSQL — transfer ItemPlacement + increment ResourceWallet
    # -----------------------------------------------------------------
    pg_success = await _transfer_to_inventory(ctx, char_id, corpse_id, instance_ids, resource_deltas)
    if not pg_success:
        log.bind(corpse_id=corpse_id).warning("LootClaimTransferFailed")
        raise RuntimeError(f"inventory transfer failed for char={char_id} corpse={corpse_id}")

    # -----------------------------------------------------------------
    # Step 2: Redis — remove claimed items from corpse, set short TTL if empty
    # -----------------------------------------------------------------
    manager = LootManager(redis_service)
    integration = LootIntegration(manager)
    claim = ClaimResultDTO(instance_ids=instance_ids, resource_deltas=resource_deltas)
    updated_corpse = await integration.mark_items_claimed(corpse_id, claim)

    if updated_corpse is None:
        log.bind(corpse_id=corpse_id).warning("LootClaimCorpseMissing")
    elif updated_corpse.is_empty:
        log.bind(corpse_id=corpse_id).info("LootClaimCorpseEmptied")

    log.bind(char_id=char_id, corpse_id=corpse_id).info("LootClaimTaskCompleted")


def _split_resource_buckets(
    resource_deltas: dict[str, int],
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    currency: dict[str, int] = {}
    resources: dict[str, int] = {}
    components: dict[str, int] = {}
    for template_id, amount in resource_deltas.items():
        if template_id.startswith(_CURRENCY_PREFIXES):
            currency[template_id] = amount
        elif template_id.startswith(_COMPONENT_PREFIXES):
            components[template_id] = amount
        else:
            resources[template_id] = amount
    return currency, resources, components


async def _transfer_to_inventory(
    ctx: dict[str, Any],
    char_id: int,
    corpse_id: str,
    instance_ids: list[str],
    resource_deltas: dict[str, int],
) -> bool:
    """
    Transfers loot to character inventory in a single PG transaction.
    Returns True on success, False on any failure (triggers ARQ retry).
    """
    try:
        async with get_session_context() as session:
            expedition_service = ExpeditionService(
                session=session,
                character_sessions=ctx.get("character_sessions"),
                expedition_manager=ctx.get("expeditions"),
            )
            expedition = await expedition_service.get_active_run(char_id, for_update=True)
            unsafe_claim = expedition is not None and expedition.status == "active"
            claim_key = _claim_key(corpse_id, instance_ids, resource_deltas)
            if (
                unsafe_claim
                and expedition is not None
                and expedition_service.expedition_repo.is_processed(expedition, claim_key)
            ):
                return True

            if instance_ids:
                await session.execute(
                    update(ItemPlacement)
                    .where(
                        ItemPlacement.item_id.in_(instance_ids),
                        ItemPlacement.holder_type.in_(["corpse", "system", "loot_pending"]),
                    )
                    .values(
                        holder_type="expedition" if unsafe_claim and expedition is not None else "character",
                        holder_id=expedition.run_id if unsafe_claim and expedition is not None else str(char_id),
                        storage_type="backpack",
                        slot=None,
                        position_index=None,
                        locked_by=None,
                    )
                )

            if resource_deltas:
                await _consume_corpse_resource_balances(session, corpse_id, resource_deltas)

            if resource_deltas and unsafe_claim and expedition is not None:
                for resource_key, amount in resource_deltas.items():
                    await increment_expedition_resource(
                        session,
                        run_id=expedition.run_id,
                        resource_key=resource_key,
                        amount=int(amount),
                        reason="unsafe_loot_claim",
                        correlation_id=claim_key,
                    )

            elif resource_deltas:
                currency_d, resources_d, components_d = _split_resource_buckets(resource_deltas)

                wallet = await session.scalar(
                    select(ResourceWallet).where(ResourceWallet.character_id == char_id).with_for_update()
                )
                if wallet is None:
                    wallet = ResourceWallet(
                        character_id=char_id,
                        currency={},
                        resources={},
                        components={},
                    )
                    session.add(wallet)
                    await session.flush()

                for tid, amt in currency_d.items():
                    wallet.currency[tid] = wallet.currency.get(tid, 0) + amt
                for tid, amt in resources_d.items():
                    wallet.resources[tid] = wallet.resources.get(tid, 0) + amt
                for tid, amt in components_d.items():
                    wallet.components[tid] = wallet.components.get(tid, 0) + amt

                flag_modified(wallet, "currency")
                flag_modified(wallet, "resources")
                flag_modified(wallet, "components")

            if unsafe_claim and expedition is not None:
                expedition_service.expedition_repo.mark_processed(expedition, claim_key)
                flag_modified(expedition, "processed_events")
                await expedition_service.refresh_session_risk(char_id, expedition=expedition, system_connect=False)

        await _clear_inventory_runtime_cache(ctx, char_id)
        return True
    except Exception:
        log.bind(char_id=char_id).exception("LootClaimTransferToInventoryFailed")
        return False


def _claim_key(corpse_id: str, instance_ids: list[str], resource_deltas: dict[str, int]) -> str:
    payload = {
        "corpse_id": corpse_id,
        "items": sorted(str(item_id) for item_id in instance_ids),
        "resources": {str(key): int(value) for key, value in sorted(resource_deltas.items())},
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return f"loot_claim:{digest}"


async def _clear_inventory_runtime_cache(ctx: dict[str, Any], char_id: int) -> None:
    redis_service = ctx.get("redis_service")
    if redis_service is None:
        return
    try:
        await InventorySessionManager(redis_service).delete(char_id)
    except Exception:
        log.bind(char_id=char_id).exception("LootClaimInventoryRuntimeCacheClearFailed")


async def _consume_corpse_resource_balances(session: Any, corpse_id: str, resource_deltas: dict[str, int]) -> None:
    for resource_key, amount in resource_deltas.items():
        if amount <= 0:
            continue
        balance = await session.scalar(
            select(ResourceBalance)
            .where(
                ResourceBalance.holder_type == "corpse",
                ResourceBalance.holder_id == corpse_id,
                ResourceBalance.resource_key == resource_key,
            )
            .with_for_update()
        )
        if balance is None:
            continue
        balance.amount = max(0, int(balance.amount or 0) - int(amount))
        if balance.amount <= 0:
            await session.delete(balance)
