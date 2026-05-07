from __future__ import annotations


class InventoryEvents:
    REWARDS_GRANT_REQUESTED = "inventory.rewards_grant_requested"
    REWARDS_GRANTED = "inventory.rewards_granted"
    REWARDS_GRANT_FAILED = "inventory.rewards_grant_failed"


__all__ = ["InventoryEvents"]
