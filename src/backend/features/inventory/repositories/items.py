from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select

from src.backend.features.items.models import ItemInstance, ItemPlacement, ItemTransaction, ResourceBalance
from src.backend.infrastructure.inventory.models import ResourceWallet
from src.shared.schemas.inventory import InventoryRuntimeItemDTO, WalletDTO

_CURRENCY_PREFIXES = ("coin_", "currency_", "gold_", "silver_", "copper_")
_COMPONENT_PREFIXES = ("essence_", "flower_", "bark_", "supply_", "component_")


class InventoryItemRepository:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def list_character_items(
        self,
        char_id: int,
        *,
        expedition_run_id: str | None = None,
    ) -> list[tuple[ItemInstance, ItemPlacement]]:
        holder_filters = [
            (ItemPlacement.holder_type == "character") & (ItemPlacement.holder_id == str(char_id)),
        ]
        if expedition_run_id:
            holder_filters.append(
                (ItemPlacement.holder_type == "expedition") & (ItemPlacement.holder_id == expedition_run_id)
            )
        holder_clause = or_(*holder_filters)
        result = await self.session.execute(
            select(ItemInstance, ItemPlacement)
            .join(ItemPlacement, ItemPlacement.item_id == ItemInstance.id)
            .where(holder_clause)
            .order_by(ItemPlacement.position_index.nulls_last(), ItemInstance.name, ItemInstance.id)
        )
        return list(result.all())

    async def get_wallet(self, char_id: int) -> WalletDTO:
        wallet = await self.session.scalar(select(ResourceWallet).where(ResourceWallet.character_id == char_id))
        if wallet is None:
            return WalletDTO()
        return WalletDTO(
            currency=dict(wallet.currency or {}),
            resources=dict(wallet.resources or {}),
            components=dict(wallet.components or {}),
        )

    async def get_expedition_wallet(self, run_id: str) -> WalletDTO:
        result = await self.session.execute(
            select(ResourceBalance.resource_key, ResourceBalance.amount).where(
                ResourceBalance.holder_type == "expedition",
                ResourceBalance.holder_id == run_id,
                ResourceBalance.storage_type == "carried",
                ResourceBalance.amount > 0,
            )
        )
        wallet = WalletDTO()
        for resource_key, amount in result.all():
            key = str(resource_key)
            value = int(amount or 0)
            if value <= 0:
                continue
            bucket = _wallet_bucket(wallet, key)
            bucket[key] = bucket.get(key, 0) + value
        return wallet

    async def save_placements(
        self,
        char_id: int,
        items: dict[str, InventoryRuntimeItemDTO],
        *,
        expedition_run_id: str | None = None,
    ) -> None:
        holder_filters = [
            (ItemPlacement.holder_type == "character") & (ItemPlacement.holder_id == str(char_id)),
        ]
        if expedition_run_id:
            holder_filters.append(
                (ItemPlacement.holder_type == "expedition") & (ItemPlacement.holder_id == expedition_run_id)
            )
        placements = {
            placement.item_id: placement
            for placement in await self.session.scalars(select(ItemPlacement).where(or_(*holder_filters)))
        }

        for item_id, item in items.items():
            placement = placements.get(item_id)
            if placement is None:
                continue
            placement.storage_type = item.placement
            placement.slot = item.slot
        await self.session.flush()

    async def save_item_mechanics(self, items: dict[str, InventoryRuntimeItemDTO]) -> None:
        if not items:
            return
        instances = {
            instance.id: instance
            for instance in await self.session.scalars(select(ItemInstance).where(ItemInstance.id.in_(items)))
        }
        for item_id, item in items.items():
            instance = instances.get(item_id)
            if instance is None:
                continue
            instance.mechanics = dict(item.mechanics)
        await self.session.flush()

    async def discard_character_item(
        self,
        char_id: int,
        item_id: str,
        *,
        expedition_run_id: str | None = None,
        reason: str = "inventory_drop",
    ) -> bool:
        holder_filters = [
            (ItemPlacement.holder_type == "character") & (ItemPlacement.holder_id == str(char_id)),
        ]
        if expedition_run_id:
            holder_filters.append(
                (ItemPlacement.holder_type == "expedition") & (ItemPlacement.holder_id == expedition_run_id)
            )
        placement = await self.session.scalar(
            select(ItemPlacement).where(
                ItemPlacement.item_id == item_id,
                or_(*holder_filters),
            )
        )
        if placement is None:
            return False

        self.session.add(
            ItemTransaction(
                item_id=placement.item_id,
                from_holder_type=placement.holder_type,
                from_holder_id=placement.holder_id,
                from_storage_type=placement.storage_type,
                to_holder_type="system",
                to_holder_id=f"discarded:{char_id}",
                to_storage_type="discarded",
                reason=reason,
            )
        )
        placement.holder_type = "system"
        placement.holder_id = f"discarded:{char_id}"
        placement.storage_type = "discarded"
        placement.slot = None
        placement.position_index = None
        placement.locked_by = None
        await self.session.flush()
        return True

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()


def _wallet_bucket(wallet: WalletDTO, key: str) -> dict[str, int]:
    if key.startswith(_CURRENCY_PREFIXES):
        return wallet.currency
    if key.startswith(_COMPONENT_PREFIXES):
        return wallet.components
    return wallet.resources


def runtime_item_from_instance(instance: ItemInstance, placement: ItemPlacement) -> InventoryRuntimeItemDTO:
    mechanics = dict(instance.mechanics or {})
    metadata = {**dict(instance.metadata_ or {}), **dict(getattr(instance, "appearance", {}) or {})}
    slot = placement.slot or mechanics.get("slot")
    if slot:
        mechanics["slot"] = slot

    valid_slots = mechanics.get("valid_slots")
    if not isinstance(valid_slots, list):
        valid_slots = [slot] if slot else []

    is_unsecured = getattr(placement, "holder_type", "character") == "expedition"
    return InventoryRuntimeItemDTO(
        item_id=str(instance.id),
        base_id=instance.base_id,
        item_type=instance.item_type,
        slot=str(slot) if slot else None,
        valid_slots=[str(value) for value in valid_slots if value],
        placement=placement.storage_type,
        name=instance.name,
        description=instance.description,
        rarity=instance.rarity,
        rarity_tier=instance.rarity_tier,
        quantity=_quantity_from_item(metadata, mechanics),
        sync_state="unsecured" if is_unsecured else "secured",
        is_unsecured=is_unsecured,
        mechanics=mechanics,
        tags=list((instance.generation or {}).get("narrative_tags") or []),
        metadata=metadata,
    )


def _quantity_from_item(metadata: dict[str, Any], mechanics: dict[str, Any]) -> int:
    for raw in (
        metadata.get("quantity"),
        metadata.get("stack_count"),
        metadata.get("count"),
        mechanics.get("quantity"),
        mechanics.get("stack_count"),
        mechanics.get("charges"),
    ):
        if raw is not None:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return 1
