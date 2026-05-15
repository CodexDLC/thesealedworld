from __future__ import annotations

import random

from src.backend.features.loot.resources.resolver import resolve_resource
from src.backend.features.loot.resources.types import (
    EquipmentEntry,
    ResourceEntry,
    RoleLootProfile,
)
from src.shared.schemas.loot import LootItemDTO

# Probability weights for tier modifier by monster role.
# boss never drops below its tier (-1 weight = 0).
_TIER_WEIGHTS: dict[str, list[tuple[int, float]]] = {
    "minion": [(-1, 0.70), (0, 0.25), (1, 0.05)],
    "veteran": [(-1, 0.50), (0, 0.40), (1, 0.10)],
    "elite": [(-1, 0.30), (0, 0.55), (1, 0.15)],
    "boss": [(-1, 0.00), (0, 0.80), (1, 0.20)],
}
_DEFAULT_WEIGHTS = _TIER_WEIGHTS["minion"]


class LootEngine:
    """Pure dice logic. No Redis, no DB, no imports from services."""

    def roll_tier_modifier(self, role: str) -> int:
        weights = _TIER_WEIGHTS.get(role, _DEFAULT_WEIGHTS)
        modifiers = [m for m, _ in weights]
        probabilities = [w for _, w in weights]
        return random.choices(modifiers, weights=probabilities, k=1)[0]

    def roll_amount(self, amount_range: tuple[int, int]) -> int:
        lo, hi = amount_range
        return random.randint(lo, hi) if lo < hi else lo

    def build_drop_items(
        self,
        profile: RoleLootProfile,
        monster_tier: int,
        role: str,
        battle_type: str,
    ) -> list[LootItemDTO]:
        items: list[LootItemDTO] = []
        for entry in profile.drop:
            if random.random() >= entry.chance:
                continue
            if isinstance(entry, ResourceEntry):
                if entry.profile == "currency" and battle_type == "arena":
                    continue
                tier = (
                    entry.fixed_tier
                    if entry.fixed_tier is not None
                    else max(0, monster_tier + self.roll_tier_modifier(role))
                )
                template_id = resolve_resource(entry.profile, tier)
                items.append(
                    LootItemDTO(
                        template_id=template_id,
                        name=template_id,
                        amount=self.roll_amount(entry.amount_range),
                        layer="drop",
                        is_resource=True,
                    )
                )
            elif isinstance(entry, EquipmentEntry):
                # Equipment entries return a request dict consumed by LootService → Item Service
                items.append(
                    LootItemDTO(
                        template_id=entry.base_id,
                        name=entry.base_id,
                        layer="drop",
                        is_resource=False,
                    )
                )
        return items

    def build_salvage_items(
        self,
        profile: RoleLootProfile,
        monster_tier: int,
        role: str,
    ) -> list[LootItemDTO]:
        items: list[LootItemDTO] = []
        for entry in profile.salvage:
            if random.random() >= entry.chance:
                continue
            tier = (
                entry.fixed_tier
                if entry.fixed_tier is not None
                else max(0, monster_tier + self.roll_tier_modifier(role))
            )
            template_id = resolve_resource(entry.profile, tier)
            items.append(
                LootItemDTO(
                    template_id=template_id,
                    name=template_id,
                    amount=self.roll_amount(entry.amount_range),
                    layer="salvage",
                    is_resource=True,
                )
            )
        return items

    def build_spoil_items(
        self,
        profile: RoleLootProfile,
        monster_tier: int,
        role: str,
    ) -> list[LootItemDTO]:
        # Spoil skill not implemented yet — always returns empty
        return []

    def roll_equipment_tier(self, monster_tier: int, role: str) -> int:
        return max(0, monster_tier + self.roll_tier_modifier(role))
