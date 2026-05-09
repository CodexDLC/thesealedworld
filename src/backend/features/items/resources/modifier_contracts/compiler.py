from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import ModifierContractDTO


def compile_modifier_command(contract: ModifierContractDTO, value: float) -> str:
    """Compile a modifier value into the StatsWaterfallCalculator command language."""
    if contract.operation == "add":
        return f"+{_format_number(value)}" if value >= 0 else _format_number(value)
    if contract.operation == "mult":
        return f"*{_format_number(round(1.0 + value, 6))}"
    if contract.operation == "set":
        return f"={_format_number(value)}"
    raise ValueError(f"Unknown modifier operation: {contract.operation!r}")


def _format_number(value: float) -> str:
    rounded = round(float(value), 6)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.6f}".rstrip("0").rstrip(".")
