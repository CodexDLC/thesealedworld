from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class LootEntry:
    template_id: str
    item_type: Literal["resource", "equipment", "currency"]
    tier: int
    drop_chance: float
    amount_range: tuple[int, int] = (1, 1)
    rarity_pool: tuple[str, ...] = ()


@dataclass(frozen=True)
class LootScheme:
    id: str
    entries: Sequence[LootEntry] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResourceEntry:
    profile: str  # "hide" | "bones" | "currency"
    chance: float  # 0.0–1.0
    amount_range: tuple[int, int] = (1, 1)
    fixed_tier: int | None = None  # None = resolve by monster tier ±1 roll


@dataclass(frozen=True)
class EquipmentEntry:
    base_id: str  # Item Service base_id
    chance: float


@dataclass
class RoleLootProfile:
    drop: Sequence[ResourceEntry | EquipmentEntry] = field(default_factory=list)
    salvage: Sequence[ResourceEntry] = field(default_factory=list)
    spoil: Sequence[ResourceEntry] = field(default_factory=list)


@dataclass
class MonsterLootProfile:
    id: str
    archetype: Literal["beast", "humanoid", "construct"]
    roles: dict[str, RoleLootProfile] = field(default_factory=dict)

    def get_role(self, role: str) -> RoleLootProfile:
        return self.roles.get(role) or self.roles.get("minion") or RoleLootProfile()
