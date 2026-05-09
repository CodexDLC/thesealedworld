from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from ..modifier_contracts import MODIFIER_CONTRACTS
from .bundles import ALL_BUNDLES
from .definitions import ALL_AFFIX_DEFINITIONS

if TYPE_CHECKING:
    from .schemas import AffixBundleDTO, AffixCatalogEntryDTO

AFFIX_CATALOG: dict[str, AffixCatalogEntryDTO] = {entry.id: entry for entry in ALL_AFFIX_DEFINITIONS}

BUNDLE_CATALOG: dict[str, AffixBundleDTO] = {bundle.id: bundle for bundle in ALL_BUNDLES}

_duplicate_affix_ids = [
    affix_id for affix_id, count in Counter(entry.id for entry in ALL_AFFIX_DEFINITIONS).items() if count > 1
]
if _duplicate_affix_ids:
    raise ValueError(f"Duplicate affix catalog ids: {', '.join(_duplicate_affix_ids)}")

_duplicate_bundle_ids = [
    bundle_id for bundle_id, count in Counter(bundle.id for bundle in ALL_BUNDLES).items() if count > 1
]
if _duplicate_bundle_ids:
    raise ValueError(f"Duplicate affix bundle ids: {', '.join(_duplicate_bundle_ids)}")

_missing_modifier_contracts = [
    (entry.id, entry.technical.modifier_id)
    for entry in ALL_AFFIX_DEFINITIONS
    if entry.technical.modifier_id not in MODIFIER_CONTRACTS
]
if _missing_modifier_contracts:
    raise ValueError(
        "Affix entries reference unknown modifier contracts: "
        + ", ".join(f"{affix}->{modifier}" for affix, modifier in _missing_modifier_contracts)
    )

_missing = [
    (bundle.id, affix_id) for bundle in ALL_BUNDLES for affix_id in bundle.affix_ids if affix_id not in AFFIX_CATALOG
]
if _missing:
    raise ValueError(
        "Bundle affix_ids reference unknown affix catalog entries: " + ", ".join(f"{b}→{a}" for b, a in _missing)
    )
