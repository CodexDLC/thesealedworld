from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.approach import (
    BEAST_APPROACH_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.contact_vs_beast import (
    BEAST_CONTACT_VS_BEAST_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.contact_vs_humanoid import (
    BEAST_CONTACT_VS_HUMANOID_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.impact_vs_beast import (
    BEAST_IMPACT_VS_BEAST_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.impact_vs_humanoid import (
    BEAST_IMPACT_VS_HUMANOID_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.natural_weapons import (
    BEAST_NATURAL_WEAPON_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.beast.reaction import (
    BEAST_REACTION_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.approach import (
    HUMANOID_APPROACH_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.contact_vs_beast import (
    HUMANOID_CONTACT_VS_BEAST_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.contact_vs_humanoid import (
    HUMANOID_CONTACT_VS_HUMANOID_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.impact_vs_beast import (
    HUMANOID_IMPACT_VS_BEAST_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.impact_vs_humanoid import (
    HUMANOID_IMPACT_VS_HUMANOID_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.reaction import (
    HUMANOID_REACTION_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.bodies.humanoid.weapon_forms import (
    HUMANOID_WEAPON_FORM_PHRASES,
)
from src.backend.features.game_catalog.combat.resources.text_fragments.common.result import COMMON_RESULT_PHRASES
from src.backend.features.game_catalog.combat.resources.text_fragments.death.beast import DEATH_BEAST_PHRASES
from src.backend.features.game_catalog.combat.resources.text_fragments.death.common import DEATH_COMMON_PHRASES
from src.backend.features.game_catalog.combat.resources.text_fragments.death.humanoid import DEATH_HUMANOID_PHRASES
from src.backend.features.game_catalog.combat.resources.text_templates.schemas import CombatTextPhraseDTO

if TYPE_CHECKING:
    from collections.abc import Mapping

PHRASE_SOURCES: tuple[Mapping[str, Mapping[str, dict[str, Any]]], ...] = (
    COMMON_RESULT_PHRASES,
    HUMANOID_APPROACH_PHRASES,
    HUMANOID_CONTACT_VS_HUMANOID_PHRASES,
    HUMANOID_CONTACT_VS_BEAST_PHRASES,
    HUMANOID_IMPACT_VS_HUMANOID_PHRASES,
    HUMANOID_IMPACT_VS_BEAST_PHRASES,
    HUMANOID_REACTION_PHRASES,
    HUMANOID_WEAPON_FORM_PHRASES,
    BEAST_APPROACH_PHRASES,
    BEAST_CONTACT_VS_HUMANOID_PHRASES,
    BEAST_CONTACT_VS_BEAST_PHRASES,
    BEAST_IMPACT_VS_HUMANOID_PHRASES,
    BEAST_IMPACT_VS_BEAST_PHRASES,
    BEAST_REACTION_PHRASES,
    BEAST_NATURAL_WEAPON_PHRASES,
    DEATH_COMMON_PHRASES,
    DEATH_HUMANOID_PHRASES,
    DEATH_BEAST_PHRASES,
)


def load_combat_text_phrases() -> dict[str, CombatTextPhraseDTO]:
    phrases: dict[str, CombatTextPhraseDTO] = {}
    for source in PHRASE_SOURCES:
        for kind, entries in source.items():
            for key, raw in entries.items():
                if key in phrases:
                    raise ValueError(f"Duplicate combat text phrase key: {key}")
                phrase = CombatTextPhraseDTO.model_validate({"key": key, **raw})
                if phrase.kind != kind:
                    raise ValueError(f"Phrase {key} kind {phrase.kind} does not match bucket {kind}")
                phrases[key] = phrase
    return phrases
