from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder
    from src.backend.features.character.runtime.combat_math_model import (
        CharacterCombatMathModelBuilder,
        RawCombatMathModel,
        RawStatBlock,
    )
    from src.backend.features.character.runtime.vitals import CharacterVitalsCalculator, VitalFormulaResult

__all__ = [
    "CharacterCombatActorInputBuilder",
    "CharacterCombatMathModelBuilder",
    "CharacterVitalsCalculator",
    "RawCombatMathModel",
    "RawStatBlock",
    "VitalFormulaResult",
]


def __getattr__(name: str) -> Any:
    if name == "CharacterCombatActorInputBuilder":
        from src.backend.features.character.runtime.combat_actor_input import CharacterCombatActorInputBuilder

        return CharacterCombatActorInputBuilder
    if name in {"CharacterCombatMathModelBuilder", "RawCombatMathModel", "RawStatBlock"}:
        from src.backend.features.character.runtime.combat_math_model import (
            CharacterCombatMathModelBuilder,
            RawCombatMathModel,
            RawStatBlock,
        )

        return {
            "CharacterCombatMathModelBuilder": CharacterCombatMathModelBuilder,
            "RawCombatMathModel": RawCombatMathModel,
            "RawStatBlock": RawStatBlock,
        }[name]
    if name in {"CharacterVitalsCalculator", "VitalFormulaResult"}:
        from src.backend.features.character.runtime.vitals import CharacterVitalsCalculator, VitalFormulaResult

        return {
            "CharacterVitalsCalculator": CharacterVitalsCalculator,
            "VitalFormulaResult": VitalFormulaResult,
        }[name]
    raise AttributeError(name)
