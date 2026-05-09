from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AffixRollProfileDTO:
    step_spread: float
    # "decimal" | "floor_int" | "round_int"
    rounding: str
    round_digits: int = 4


@dataclass(frozen=True)
class AffixTechnicalDTO:
    modifier_id: str
    base_value: float
    # "probability" | "flat_decimal" | "flat_int" | "multiplier_delta"
    value_kind: str
    roll_profile: AffixRollProfileDTO
    min_item_tier: int = 0
    required_item_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AffixDescriptiveDTO:
    display_name: str
    # "{value}" is the single injection point, pre-formatted by value_kind.
    ui_template: str
    narrative_tags: tuple[str, ...]


@dataclass(frozen=True)
class AffixCatalogEntryDTO:
    id: str
    group: str
    technical: AffixTechnicalDTO
    descriptive: AffixDescriptiveDTO


@dataclass(frozen=True)
class AffixBundleDTO:
    id: str
    size: int
    affix_ids: tuple[str, ...]
    allowed_item_types: tuple[str, ...]
    min_item_tier: int
    tags: tuple[str, ...]
    source_constraints: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.size != len(self.affix_ids):
            raise ValueError(f"Bundle {self.id!r}: size={self.size} but affix_ids has {len(self.affix_ids)} entries")
