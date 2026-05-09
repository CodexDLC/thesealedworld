from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .definitions import MODIFIER_CONTRACT_DEFINITIONS

if TYPE_CHECKING:
    from .schemas import ModifierContractDTO

MODIFIER_CONTRACTS: dict[str, ModifierContractDTO] = {
    contract.id: contract for contract in MODIFIER_CONTRACT_DEFINITIONS
}

_duplicate_ids = [
    contract_id
    for contract_id, count in Counter(contract.id for contract in MODIFIER_CONTRACT_DEFINITIONS).items()
    if count > 1
]
if _duplicate_ids:
    raise ValueError(f"Duplicate modifier contract ids: {', '.join(_duplicate_ids)}")

_bad_operations = [
    contract.id for contract in MODIFIER_CONTRACT_DEFINITIONS if contract.operation not in {"add", "mult", "set"}
]
if _bad_operations:
    raise ValueError(f"Modifier contracts use unknown operations: {', '.join(_bad_operations)}")


def get_modifier_contract(contract_id: str) -> ModifierContractDTO | None:
    return MODIFIER_CONTRACTS.get(contract_id)
