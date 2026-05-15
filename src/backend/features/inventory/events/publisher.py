from __future__ import annotations


class InventoryEvents:
    REWARDS_GRANT_REQUESTED = "inventory.rewards_grant_requested"
    REWARDS_GRANTED = "inventory.rewards_granted"
    REWARDS_GRANT_FAILED = "inventory.rewards_grant_failed"
    DURABILITY_DAMAGE_REQUESTED = "inventory.durability_damage_requested"
    DURABILITY_DAMAGE_APPLIED = "inventory.durability_damage_applied"
    DURABILITY_DAMAGE_FAILED = "inventory.durability_damage_failed"


__all__ = ["InventoryEvents"]
