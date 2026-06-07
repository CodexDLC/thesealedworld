from __future__ import annotations

import random
from typing import Any

from src.backend.features.loot.resources.equipment_pool import merged_pool
from src.backend.features.loot.resources.resolver import resolve_resource
from src.backend.features.loot.resources.types import (
    FamilyEquipmentProfile,
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
        *,
        chance_multiplier: float = 1.0,
    ) -> list[LootItemDTO]:
        items: list[LootItemDTO] = []
        for entry in profile.drop:
            chance = min(1.0, entry.chance * max(0.0, chance_multiplier))
            if random.random() >= chance:
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

    def pick_equipment_base_id(
        self,
        eq_profile: FamilyEquipmentProfile,
        role: str,
        *,
        chance_multiplier: float = 1.0,
    ) -> str | None:
        chance = min(1.0, eq_profile.role_chances.get(role, eq_profile.default_chance) * max(0.0, chance_multiplier))
        if random.random() >= chance:
            return None
        pool = merged_pool(eq_profile.enabled_subcategories)
        if not pool:
            return None
        return random.choice(pool)

    def build_group_bonus_item(
        self,
        candidates: list[Any],
        *,
        chance_multiplier: float = 1.0,
    ) -> tuple[Any, str] | None:
        if not candidates:
            return None
        candidate = random.choice(candidates)
        base_id = self.pick_equipment_base_id(
            candidate.eq_profile,
            candidate.role,
            chance_multiplier=chance_multiplier,
        )
        if base_id is None:
            return None
        return candidate, base_id
